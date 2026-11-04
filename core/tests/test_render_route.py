"""Tests POST /render through the engine app, reading responses as a multipart/form-data client would."""

import io
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from diplex.api import create_app, render_route
from diplex.api.upload_limit_setting import MAX_UPLOAD_BYTES_VARIABLE
from diplex.definition import RenderError, RenderErrorCode, RenderManifest
from diplex.engine import DocxConversionError, PageTooLargeError, UnoserverUnavailableError, document_render
from diplex.engine.pages import read_page_sizes

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"


def _sample_bytes(sample_name: str) -> bytes:
    """Read a sample, skipping the test when it isn't in samples/."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")
    return sample_path.read_bytes()


def _post_render(document_bytes: bytes, file_name: str = "upload.pdf", content_type: str = "application/pdf"):
    """Send the bytes to /render as the document part of a multipart/form-data upload."""
    with TestClient(create_app()) as client:
        return client.post("/render", files={"document": (file_name, document_bytes, content_type)})


def _response_parts(response) -> list:
    """Parse a multipart/form-data response into its parts with the standard library."""
    head = f"Content-Type: {response.headers['content-type']}\r\n\r\n".encode()
    message = BytesParser(policy=policy.HTTP).parsebytes(head + response.content)
    assert message.is_multipart()
    return list(message.iter_parts())


def _error(response) -> RenderError:
    """Read an error response's body as the contract's RenderError."""
    assert response.headers["content-type"] == "application/json"
    return RenderError.model_validate_json(response.content)


def test_a_pdf_comes_back_as_its_manifest_and_one_webp_per_page():
    """The UN resolution's 12 pages come back as the manifest part, then 12 lossless WebP parts in page order."""
    pdf_bytes = _sample_bytes("un-resolution-78-1-en.pdf")

    response = _post_render(pdf_bytes)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/form-data; boundary=")
    manifest_part, *page_parts = _response_parts(response)
    assert manifest_part.get_param("name", header="content-disposition") == "manifest"
    assert manifest_part.get_filename() is None
    assert manifest_part.get_content_type() == "application/json"
    manifest = RenderManifest.model_validate_json(manifest_part.get_payload(decode=True))
    assert manifest.pages == read_page_sizes(pdf_bytes)
    assert len(page_parts) == len(manifest.pages) == 12
    for page_size, page_part in zip(manifest.pages, page_parts, strict=True):
        assert page_part.get_param("name", header="content-disposition") == "page"
        assert page_part.get_filename() == f"page-{page_size.index:04d}.webp"
        assert page_part.get_content_type() == "image/webp"
        with Image.open(io.BytesIO(page_part.get_payload(decode=True))) as page_image:
            assert (page_image.format, page_image.size) == ("WEBP", (1224, 1584))


def test_a_pdf_upload_gets_no_pdf_back():
    """A PDF upload's response has no pdf part (ADR 010)."""
    response = _post_render(_sample_bytes("irs-form-1040-2025.pdf"))

    part_names = [part.get_param("name", header="content-disposition") for part in _response_parts(response)]
    assert part_names == ["manifest", "page", "page"]


def test_the_file_name_and_content_type_sent_are_ignored():
    """A PDF sent as notes.txt with text/plain is still rendered: the type comes from the bytes."""
    response = _post_render(_sample_bytes("irs-form-1040-2025.pdf"), file_name="notes.txt", content_type="text/plain")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "upload_bytes", [b"", b"Plain text, not a document.\n", b"<html>%PDF-1.7</html>"], ids=["empty", "text", "html"]
)
def test_a_non_document_gets_415(upload_bytes):
    """Anything but a PDF or a DOCX is refused with 415 and the unsupported_document_type code."""
    response = _post_render(upload_bytes)

    assert response.status_code == 415
    assert _error(response).code is RenderErrorCode.UNSUPPORTED_DOCUMENT_TYPE


def test_a_docx_comes_back_with_the_pdf_it_became(monkeypatch):
    """A DOCX is converted, rendered through the PDF path, and its PDF comes back as the last part, document.pdf."""
    converted_pdf = _sample_bytes("irs-form-1040-2025.pdf")  # stands in for unoserver's output
    converted_docx = []
    monkeypatch.setattr(document_render, "convert_docx_to_pdf", lambda docx_bytes: converted_docx.append(docx_bytes) or converted_pdf)
    docx_bytes = _sample_bytes("siu-dissertation-template.docx")

    response = _post_render(docx_bytes, file_name="thesis.docx")

    assert response.status_code == 200
    assert converted_docx == [docx_bytes]
    manifest_part, *page_parts, pdf_part = _response_parts(response)
    assert RenderManifest.model_validate_json(manifest_part.get_payload(decode=True)).pages == read_page_sizes(converted_pdf)
    assert [part.get_filename() for part in page_parts] == ["page-0001.webp", "page-0002.webp"]
    assert pdf_part.get_param("name", header="content-disposition") == "pdf"
    assert pdf_part.get_filename() == "document.pdf"
    assert pdf_part.get_content_type() == "application/pdf"
    assert pdf_part.get_payload(decode=True) == converted_pdf


def test_a_docx_gets_503_when_unoserver_is_not_answering(monkeypatch):
    """If unoserver can't be reached, the upload gets 503 converter_unavailable, to retry later."""

    def unreachable_unoserver(docx_bytes):
        """Fail as convert_docx_to_pdf does when nothing listens on unoserver's port."""
        raise UnoserverUnavailableError("unoserver is not answering on http://127.0.0.1:2003: connection refused")

    monkeypatch.setattr(document_render, "convert_docx_to_pdf", unreachable_unoserver)

    response = _post_render(_sample_bytes("siu-dissertation-template.docx"), file_name="thesis.docx")

    assert response.status_code == 503
    assert _error(response).code is RenderErrorCode.CONVERTER_UNAVAILABLE


def test_a_docx_libreoffice_cannot_load_gets_422_with_a_plain_message(monkeypatch):
    """A failed conversion gets 422 docx_conversion_failed, without unoserver's message about LibreOffice's internals."""
    unoserver_message = "<class 'RuntimeError'>:Could not load document <remote file> using the MS Word 2007 XML filter."

    def failing_conversion(docx_bytes):
        """Fail as convert_docx_to_pdf does when LibreOffice can't load the document."""
        raise DocxConversionError(f"unoserver could not convert the document: {unoserver_message}")

    monkeypatch.setattr(document_render, "convert_docx_to_pdf", failing_conversion)

    response = _post_render(_sample_bytes("siu-dissertation-template.docx"), file_name="thesis.docx")

    assert response.status_code == 422
    assert _error(response) == RenderError(
        code=RenderErrorCode.DOCX_CONVERSION_FAILED, message="LibreOffice could not load or convert the DOCX"
    )
    assert b"RuntimeError" not in response.content


def test_a_pdf_pdfium_cannot_read_gets_422():
    """Bytes that start like a PDF but aren't one get 422 and unreadable_pdf."""
    response = _post_render(b"%PDF-1.7\nnot really a PDF\n")

    assert response.status_code == 422
    assert _error(response).code is RenderErrorCode.UNREADABLE_PDF


def test_a_page_too_large_gets_422_with_its_page_number(monkeypatch):
    """A page over the pixel limits gets 422 and page_too_large, and the message says which page."""

    def refuse_page_two(pdf_bytes):
        """Fail as render_pdf does on a page too large to render."""
        raise PageTooLargeError("page 2 would render at 28800 x 28800 pixels, over the limit of 40,000,000")

    monkeypatch.setattr(render_route, "render_pdf", refuse_page_two)

    response = _post_render(b"%PDF-1.7 stand-in")

    assert response.status_code == 422
    assert _error(response).code is RenderErrorCode.PAGE_TOO_LARGE
    assert "page 2" in _error(response).message


def test_a_request_without_the_document_part_gets_422_invalid_request():
    """A form without a document part gets 422 invalid_request, not FastAPI's answer that quotes what was sent."""
    with TestClient(create_app()) as client:
        response = client.post("/render", data={"wrong_name": "Text from the document"})

    assert response.status_code == 422
    assert _error(response).code is RenderErrorCode.INVALID_REQUEST
    assert b"Text from the document" not in response.content


def test_a_body_that_is_not_multipart_gets_400_invalid_request():
    """A multipart content type over a body FastAPI can't parse gets 400 invalid_request."""
    with TestClient(create_app()) as client:
        response = client.post(
            "/render", content=b"not multipart at all", headers={"content-type": "multipart/form-data; boundary=missing"}
        )

    assert response.status_code == 400
    assert _error(response).code is RenderErrorCode.INVALID_REQUEST


def test_other_http_errors_keep_fastapis_answer():
    """A route that doesn't exist still gets FastAPI's 404."""
    with TestClient(create_app()) as client:
        response = client.get("/no-such-route")

    assert (response.status_code, response.json()) == (404, {"detail": "Not Found"})


def test_an_upload_over_the_limit_gets_413_without_rendering(monkeypatch):
    """With DIPLEX_MAX_UPLOAD_BYTES below the sample's size, the upload gets 413, even when sent chunked."""
    monkeypatch.setenv(MAX_UPLOAD_BYTES_VARIABLE, "100000")
    rendered_uploads = []
    monkeypatch.setattr(render_route, "render_pdf", rendered_uploads.append)
    pdf_bytes = _sample_bytes("irs-form-1040-2025.pdf")  # 220 KB

    with TestClient(create_app()) as client:
        whole_response = client.post("/render", files={"document": ("upload.pdf", pdf_bytes, "application/pdf")})
    boundary = "test-boundary"
    multipart_body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="upload.pdf"\r\n\r\n'.encode()
        + pdf_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    chunks = (multipart_body[start : start + 8192] for start in range(0, len(multipart_body), 8192))
    with TestClient(create_app()) as client:
        chunked_response = client.post(
            "/render", content=chunks, headers={"content-type": f"multipart/form-data; boundary={boundary}"}
        )

    assert (whole_response.status_code, chunked_response.status_code) == (413, 413)
    assert _error(chunked_response).code is RenderErrorCode.UPLOAD_TOO_LARGE
    assert rendered_uploads == []
