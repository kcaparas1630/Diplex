"""The JSON body of an engine error response: a code to branch on and a message to read."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RenderErrorCode(StrEnum):
    """What went wrong, for consumers to branch on."""

    INVALID_REQUEST = "invalid_request"  # 400 or 422: not multipart/form-data with a file part named document
    UNAUTHORIZED = "unauthorized"  # 401: the engine has DIPLEX_API_KEY set and the request didn't send it
    UNSUPPORTED_API_VERSION = "unsupported_api_version"  # 400: no Diplex-Api-Version header, or one this engine doesn't serve
    UPLOAD_TOO_LARGE = "upload_too_large"  # 413: the request body is over the engine's upload limit
    UNSUPPORTED_DOCUMENT_TYPE = "unsupported_document_type"  # 415: the upload is not a PDF or a DOCX
    UNREADABLE_PDF = "unreadable_pdf"  # 422: the PDF is damaged, encrypted or not really a PDF
    PAGE_TOO_LARGE = "page_too_large"  # 422: a page's image would be over the pixel limits
    DOCX_CONVERSION_FAILED = "docx_conversion_failed"  # 422: LibreOffice could not load or convert the DOCX
    CONVERTER_UNAVAILABLE = "converter_unavailable"  # 503: unoserver, which converts a DOCX, is not answering
    CONVERTER_BUSY = "converter_busy"  # 503: every unoserver instance stayed busy for DIPLEX_CONVERTER_WAIT_SECONDS
    INTERNAL_ERROR = "internal_error"  # 500: the engine failed; its log has the job ID from the message


class RenderError(BaseModel):
    """An error response's body."""

    code: RenderErrorCode = Field(description="What went wrong; new codes may be added, so handle unknown ones.")
    message: str = Field(description="What went wrong in plain words, for logs. Never repeats document contents.")
