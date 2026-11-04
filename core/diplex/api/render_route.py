"""POST /render: a PDF in, its page sizes and lossless WebP page images out, as multipart/form-data (ADR 010)."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.status import (
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

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
from .job_log import RenderJob, log_unexpected_error, logged_render_job

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
    with logged_render_job(len(document_bytes)) as render_job:
        try:
            response_body, content_type = _render(document_bytes, render_job)
        except tuple(ERROR_RESPONSES) as error:
            status_code, error_code = ERROR_RESPONSES[type(error)]
            return _error_response(render_job, status_code, error_code, str(error))  # engine messages hold no contents
        except Exception as error:
            # Answered here, so the server never logs the error's message, which could quote the document.
            log_unexpected_error(render_job, error)
            message = f"the engine failed on this document; its log has job {render_job.job_id}"
            return _error_response(render_job, HTTP_500_INTERNAL_SERVER_ERROR, RenderErrorCode.INTERNAL_ERROR, message)
    return Response(content=response_body, media_type=content_type)


def _render(document_bytes: bytes, render_job: RenderJob) -> tuple[bytes, str]:
    """Render the upload into the response body and its content type, noting the job's type and page count."""
    document_type = detect_document_type(document_bytes)
    render_job.source_type = document_type.value
    if document_type is not DocumentType.PDF:
        raise UnsupportedDocumentError("only PDF uploads are rendered so far")
    rendered_document = render_pdf(document_bytes)
    render_job.page_count = len(rendered_document.page_sizes)
    return encode_form_data(_response_parts(rendered_document))


def _error_response(render_job: RenderJob, status_code: int, error_code: RenderErrorCode, message: str) -> JSONResponse:
    """Answer with the contract's error body, noting the code as the job's outcome."""
    render_job.outcome = error_code.value
    return JSONResponse(RenderError(code=error_code, message=message).model_dump(mode="json"), status_code=status_code)


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
