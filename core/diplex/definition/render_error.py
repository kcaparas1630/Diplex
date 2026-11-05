"""The JSON body of an engine error response: a code to branch on and a message to read."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RenderErrorCode(StrEnum):
    """What went wrong, for consumers to branch on."""

    UPLOAD_TOO_LARGE = "upload_too_large"  # 413: the request body is over the engine's upload limit
    UNSUPPORTED_DOCUMENT_TYPE = "unsupported_document_type"  # 415: the upload is not a PDF or a DOCX
    UNREADABLE_PDF = "unreadable_pdf"  # 422: the PDF is damaged, encrypted or not really a PDF
    PAGE_TOO_LARGE = "page_too_large"  # 422: a page's image would be over the pixel limits
    INTERNAL_ERROR = "internal_error"  # 500: the engine failed; its log has the job ID from the message


class RenderError(BaseModel):
    """An error response's body."""

    code: RenderErrorCode = Field(description="What went wrong; new codes may be added, so handle unknown ones.")
    message: str = Field(description="What went wrong in plain words, for logs. Never repeats document contents.")
