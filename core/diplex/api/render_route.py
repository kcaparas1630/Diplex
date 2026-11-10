"""POST /render: a DOCX or PDF in; its page sizes, WebP page images and any converted PDF out, as multipart/form-data."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.datastructures import State
from starlette.status import (
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from diplex.definition import (
    CONVERTED_PDF_FILENAME,
    RENDER_PART_MEDIA_TYPES,
    RenderError,
    RenderErrorCode,
    RenderManifest,
    RenderPart,
    RenderResponseParts,
)
from diplex.engine import (
    ConverterBusyError,
    DamagedDocxError,
    DocumentType,
    DocxConversionError,
    DocxConversionTimeoutError,
    DocxLimitsExceededError,
    MacroEnabledDocumentError,
    PageTooLargeError,
    RenderedDocument,
    TooManyPagesError,
    UnoserverPool,
    UnoserverUnavailableError,
    UnreadablePdfError,
    UnsupportedDocumentError,
    detect_document_type,
    render_docx,
    render_pdf,
)

from .api_key import require_api_key
from .api_version import require_supported_api_version
from .form_data import FormDataPart, encode_form_data
from .job_log import RenderJob, log_unexpected_error, logged_render_job

render_router = APIRouter(tags=["render"])

# Each engine error, the status it answers with (RFC 9110 §15.5 and §15.6) and its code in the contract.
ERROR_RESPONSES = {
    UnsupportedDocumentError: (HTTP_415_UNSUPPORTED_MEDIA_TYPE, RenderErrorCode.UNSUPPORTED_DOCUMENT_TYPE),
    UnreadablePdfError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.UNREADABLE_PDF),
    PageTooLargeError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.PAGE_TOO_LARGE),
    TooManyPagesError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.TOO_MANY_PAGES),
    MacroEnabledDocumentError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.MACROS_NOT_ALLOWED),
    DocxLimitsExceededError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.DOCX_LIMITS_EXCEEDED),
    DamagedDocxError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.DOCX_CONVERSION_FAILED),
    DocxConversionError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.DOCX_CONVERSION_FAILED),
    DocxConversionTimeoutError: (HTTP_422_UNPROCESSABLE_CONTENT, RenderErrorCode.DOCX_CONVERSION_FAILED),
    UnoserverUnavailableError: (HTTP_503_SERVICE_UNAVAILABLE, RenderErrorCode.CONVERTER_UNAVAILABLE),
    ConverterBusyError: (HTTP_503_SERVICE_UNAVAILABLE, RenderErrorCode.CONVERTER_BUSY),
}
# What the OpenAPI spec says /render answers; every error is a RenderError in JSON.
RESPONSES_IN_SPEC = {
    200: {"model": RenderResponseParts, "description": "The page sizes and page images, as multipart/form-data."},
    400: {
        "model": RenderError,
        "description": "unsupported_api_version: no Diplex-Api-Version header, or a version this engine doesn't serve; "
        "or invalid_request: a body that isn't readable multipart/form-data.",
    },
    401: {"model": RenderError, "description": "unauthorized: the engine has DIPLEX_API_KEY set and the request didn't send it."},
    413: {"model": RenderError, "description": "upload_too_large: over DIPLEX_MAX_UPLOAD_BYTES."},
    415: {"model": RenderError, "description": "unsupported_document_type: not a PDF or a DOCX."},
    422: {
        "model": RenderError,
        "description": "invalid_request, unreadable_pdf, page_too_large, too_many_pages, docx_limits_exceeded, "
        "macros_not_allowed or docx_conversion_failed.",
    },
    500: {"model": RenderError, "description": "internal_error: the message names the job in the engine's log."},
    503: {
        "model": RenderError,
        "description": "converter_unavailable: unoserver is not answering, or converter_busy: every unoserver instance "
        "stayed busy for DIPLEX_CONVERTER_WAIT_SECONDS. Try again later.",
    },
}
# The part's own content type is ignored (the type comes from the bytes), but these are what to send.
DOCUMENT_PART_TYPES = "application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# unoserver's own message names Python classes and LibreOffice internals; the consumer gets a plain one instead.
# A timeout keeps its own message, which says how long the conversion was allowed.
FIXED_MESSAGES = {DocxConversionError: "LibreOffice could not load or convert the DOCX"}


@render_router.post(
    "/render",
    summary="Render each page of a DOCX or PDF as a WebP image",
    responses=RESPONSES_IN_SPEC,
    dependencies=[Depends(require_api_key), Depends(require_supported_api_version)],  # in this order: 401 before 400
    openapi_extra={
        "requestBody": {"content": {"multipart/form-data": {"encoding": {"document": {"contentType": DOCUMENT_PART_TYPES}}}}}
    },
)
def render_upload(document: Annotated[UploadFile, File(description="The DOCX or PDF to render.")], request: Request) -> Response:
    """Render the uploaded DOCX or PDF, answering with its page sizes, page images and any converted PDF, or an error."""
    document_bytes = document.file.read()  # the upload size limit has already capped it
    with logged_render_job(len(document_bytes)) as render_job:
        try:
            response_body, content_type = _render(document_bytes, render_job, request.app.state)
        except tuple(ERROR_RESPONSES) as error:
            status_code, error_code = ERROR_RESPONSES[type(error)]
            message = FIXED_MESSAGES.get(type(error), str(error))  # engine messages hold no document contents
            return _error_response(render_job, status_code, error_code, message)
        except Exception as error:
            # Answered here, so the server never logs the error's message, which could quote the document.
            log_unexpected_error(render_job, error)
            message = f"the engine failed on this document; its log has job {render_job.job_id}"
            return _error_response(render_job, HTTP_500_INTERNAL_SERVER_ERROR, RenderErrorCode.INTERNAL_ERROR, message)
    return Response(content=response_body, media_type=content_type)


def _render(document_bytes: bytes, render_job: RenderJob, app_state: State) -> tuple[bytes, str]:
    """Render the upload into the response body and its content type, with the app's pool and page limit."""
    document_type = detect_document_type(document_bytes)
    render_job.source_type = document_type.value
    if document_type is DocumentType.DOCX:
        unoserver_pool: UnoserverPool = app_state.unoserver_pool
        rendered_document = render_docx(document_bytes, unoserver_pool.convert_docx_to_pdf, max_pages=app_state.max_pages)
    else:
        rendered_document = render_pdf(document_bytes, max_pages=app_state.max_pages)
    render_job.page_count = len(rendered_document.page_sizes)
    return encode_form_data(_response_parts(rendered_document))


def _error_response(render_job: RenderJob, status_code: int, error_code: RenderErrorCode, message: str) -> JSONResponse:
    """Answer with the contract's error body, noting the code as the job's outcome."""
    render_job.outcome = error_code.value
    return JSONResponse(RenderError(code=error_code, message=message).model_dump(mode="json"), status_code=status_code)


def _response_parts(rendered_document: RenderedDocument) -> list[FormDataPart]:
    """Lay out the response: the manifest, one image part per page in page order, then the PDF a DOCX became."""
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
    if rendered_document.converted_pdf is None:
        return [manifest_part, *page_parts]
    converted_pdf_part = FormDataPart(
        name=RenderPart.CONVERTED_PDF,
        content_type=RENDER_PART_MEDIA_TYPES[RenderPart.CONVERTED_PDF],
        content=rendered_document.converted_pdf,
        filename=CONVERTED_PDF_FILENAME,
    )
    return [manifest_part, *page_parts, converted_pdf_part]
