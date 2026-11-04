"""Answers a request FastAPI can't read with the contract's error body, never echoing back what was sent."""

from fastapi import Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_CONTENT

from diplex.definition import RenderError, RenderErrorCode

INVALID_REQUEST_MESSAGE = "send multipart/form-data with the DOCX or PDF as a file part named document"


async def answer_invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
    """Answer a request without its document part with 422 invalid_request; FastAPI's own answer quotes the input."""
    return _invalid_request(HTTP_422_UNPROCESSABLE_CONTENT)


async def answer_http_error(request: Request, error: HTTPException) -> Response:
    """Answer FastAPI's 400 for a body it can't parse with invalid_request, and leave other errors (404, 405) to it."""
    if error.status_code != HTTP_400_BAD_REQUEST:
        return await http_exception_handler(request, error)
    return _invalid_request(HTTP_400_BAD_REQUEST)


def _invalid_request(status_code: int) -> JSONResponse:
    """Build the invalid_request error response."""
    error_body = RenderError(code=RenderErrorCode.INVALID_REQUEST, message=INVALID_REQUEST_MESSAGE)
    return JSONResponse(error_body.model_dump(mode="json"), status_code=status_code)
