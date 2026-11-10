"""Tests POST /render with real DOCX samples converted by a running unoserver on port 2003; skipped when it isn't running.

The app converts through that unoserver (scripts/start-unoserver.sh) instead of starting its own pool, which
test_unoserver_pool_with_libreoffice.py tests.
"""

import io
import math
import socket
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from diplex.api import create_app
from diplex.definition import API_VERSION_HEADER, CURRENT_API_VERSION, RenderError, RenderErrorCode, RenderManifest
from diplex.engine.docx_to_pdf import DEFAULT_UNOSERVER_PORT, convert_docx_to_pdf
from diplex.engine.pages import read_page_sizes
from stand_in_unoserver_pool import StandInUnoserverPool

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"


VERSION_HEADERS = {API_VERSION_HEADER: CURRENT_API_VERSION}  # every /render request sends it (ADR 012)


def _unoserver_is_listening() -> bool:
    """Tell whether something accepts connections on unoserver's localhost port."""
    try:
        with socket.create_connection(("127.0.0.1", DEFAULT_UNOSERVER_PORT), timeout=3):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _unoserver_is_listening(), reason=f"unoserver is not running on 127.0.0.1:{DEFAULT_UNOSERVER_PORT}"
)


def _sample_bytes(sample_name: str) -> bytes:
    """Read a sample, skipping the test when it isn't in samples/."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")
    return sample_path.read_bytes()


def _response_parts(response) -> list:
    """Parse a multipart/form-data response into its parts with the standard library."""
    head = f"Content-Type: {response.headers['content-type']}\r\n\r\n".encode()
    return list(BytesParser(policy=policy.HTTP).parsebytes(head + response.content).iter_parts())


def test_a_real_docx_comes_back_as_pages_and_the_pdf_they_were_rendered_from():
    """The SIU dissertation template: its PDF part's pages match the manifest and the page images, one for one."""
    with TestClient(create_app(unoserver_pool=StandInUnoserverPool(convert_docx_to_pdf)), headers=VERSION_HEADERS) as client:
        response = client.post(
            "/render", files={"document": ("dissertation.docx", _sample_bytes("siu-dissertation-template.docx"))}
        )

    assert response.status_code == 200
    manifest_part, *page_parts, pdf_part = _response_parts(response)
    manifest = RenderManifest.model_validate_json(manifest_part.get_payload(decode=True))
    converted_pdf = pdf_part.get_payload(decode=True)
    assert (pdf_part.get_filename(), pdf_part.get_content_type()) == ("document.pdf", "application/pdf")
    assert converted_pdf.startswith(b"%PDF-")
    assert manifest.pages == read_page_sizes(converted_pdf)
    assert len(page_parts) == len(manifest.pages) > 1
    for page_size, page_part in zip(manifest.pages, page_parts, strict=True):
        assert page_part.get_filename() == f"page-{page_size.index:04d}.webp"
        with Image.open(io.BytesIO(page_part.get_payload(decode=True))) as page_image:
            assert page_image.size == (math.ceil(page_size.width * 2), math.ceil(page_size.height * 2))


def _without_part(docx_bytes: bytes, part_name: str) -> bytes:
    """Copy a DOCX without one of its parts; its [Content_Types].xml still lists it."""
    source_package = zipfile.ZipFile(io.BytesIO(docx_bytes))
    package_buffer = io.BytesIO()
    with zipfile.ZipFile(package_buffer, "w", zipfile.ZIP_DEFLATED) as damaged_package:
        for item in source_package.infolist():
            if item.filename != part_name:
                damaged_package.writestr(item, source_package.read(item))
    return package_buffer.getvalue()


def test_the_cornell_budget_justification_now_renders():
    """The Cornell DOCX the benchmark couldn't load (it has comments) converts and renders."""
    with TestClient(create_app(unoserver_pool=StandInUnoserverPool(convert_docx_to_pdf)), headers=VERSION_HEADERS) as client:
        response = client.post(
            "/render",
            files={"document": ("budget.docx", _sample_bytes("cornell-sponsored-budget-justification.docx"))},
        )

    assert response.status_code == 200
    manifest_part, *page_parts, pdf_part = _response_parts(response)
    assert len(page_parts) == len(RenderManifest.model_validate_json(manifest_part.get_payload(decode=True)).pages)
    assert pdf_part.get_payload(decode=True).startswith(b"%PDF-")


def test_a_docx_libreoffice_cannot_load_gets_422():
    """A real DOCX missing its document part passes the type check, but LibreOffice can't load it: 422."""
    damaged_docx = _without_part(_sample_bytes("siu-dissertation-template.docx"), "word/document.xml")

    with TestClient(create_app(unoserver_pool=StandInUnoserverPool(convert_docx_to_pdf)), headers=VERSION_HEADERS) as client:
        response = client.post("/render", files={"document": ("damaged.docx", damaged_docx)})

    assert response.status_code == 422
    error = RenderError.model_validate_json(response.content)
    assert error.code is RenderErrorCode.DOCX_CONVERSION_FAILED
    assert "<remote file>" not in error.message
