"""The JSON body of an engine error response: a code to branch on and a message to read."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RenderErrorCode(StrEnum):
    """What went wrong, for consumers to branch on."""

    UPLOAD_TOO_LARGE = "upload_too_large"  # 413: the request body is over the engine's upload limit


class RenderError(BaseModel):
    """An error response's body."""

    code: RenderErrorCode = Field(description="What went wrong; new codes may be added, so handle unknown ones.")
    message: str = Field(description="What went wrong in plain words, for logs. Never repeats document contents.")
