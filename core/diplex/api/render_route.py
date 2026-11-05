"""POST /render: a PDF in, its page sizes and lossless WebP page images out, as multipart/form-data (ADR 010)."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.status import HTTP_415_UNSUPPORTED_MEDIA_TYPE, HTTP_422_UNPROCESSABLE_CONTENT

from diplex.definition import RENDER_PART_MEDIA_TYPES, RenderError, RenderErrorCode, RenderManifest, RenderPart
from diplex.engine import (
    DocumentType,
    PageTooLargeError,
    RenderedDocument,
    UnreadablePdfError,
    UnsupportedDocumentError,
    detect_document_type,
    render_pdf,
)

from .form_data import FormDataPart, encode_form_data

render_router = APIRouter(tags=["render"])

# Each engine error, the status it answers with (RFC 9110 §15.5) and its code in the contract.
ERROR_RESPONSES = {
    UnsupportedDocumentError: (HTTP_415_UNSUPPORTED_MEDIA_TYPE, RenderErrorCode.UNSUPPORTED_DOCUMENT_TYPE),
    UnreadablePdfError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.UNREADABLE_PDF),
    PageTooLargeError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.PAGE_TOO_LARGE),
}


@render_router.post("/render", summary="Render each page of a PDF as a WebP image")
def render_upload(document: Annotated[UploadFile, File(description="The PDF to render.")]) -> Response:
    """Render the uploaded PDF, answering with its page sizes and page images, or an error."""
    document_bytes = document.file.read()  # the upload size limit has already capped it
    try:
        if detect_document_type(document_bytes) is not DocumentType.PDF:
            raise UnsupportedDocumentError("only PDF uploads are rendered so far")
        rendered_document = render_pdf(document_bytes)
    except tuple(ERROR_RESPONSES) as error:
        status_code, error_code = ERROR_RESPONSES[type(error)]
        error_body = RenderError(code=error_code, message=str(error))  # engine messages never repeat document contents
        return JSONResponse(error_body.model_dump(mode="json"), status_code=status_code)
    response_body, content_type = encode_form_data(_response_parts(rendered_document))
    return Response(content=response_body, media_type=content_type)


def _response_parts(rendered_document: RenderedDocument) -> list[FormDataPart]:
    """Lay out the response: the manifest first, then one image part per page, first page first."""
    manifest = RenderManifest(pages=rendered_document.page_sizes)
    manifest_part = FormDataPart(
        name=RenderPart.MANIFEST,
        content_type=RENDER_PART_MEDIA_TYPES[RenderPart.MANIFEST],
        content=manifest.model_dump_json().encode(),
    )
    page_parts = [
        FormDataPart(
            name=RenderPart.PAGE_IMAGE,
            content_type=RENDER_PART_MEDIA_TYPES[RenderPart.PAGE_IMAGE],
            content=page_webp.webp_bytes,
            filename=page_webp.filename,
        )
        for page_webp in rendered_document.page_webps
    ]
    return [manifest_part, *page_parts]
