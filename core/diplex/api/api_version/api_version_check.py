"""Checks the Diplex-Api-Version header on /render (ADR 012): a missing or unknown version gets 400 unsupported_api_version."""

from typing import Annotated

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST

from diplex.definition import API_VERSION_HEADER, SUPPORTED_API_VERSIONS, RenderError, RenderErrorCode

API_VERSION_DESCRIPTION = f"The API version the consumer codes against. This engine serves: {', '.join(SUPPORTED_API_VERSIONS)}."


class UnsupportedApiVersionError(Exception):
    """The request sent no API version, or one this engine doesn't serve."""


def require_supported_api_version(
    api_version: Annotated[str | None, Header(alias=API_VERSION_HEADER, description=API_VERSION_DESCRIPTION)] = None,
) -> None:
    """Let a request with a supported version through; raise UnsupportedApiVersionError otherwise."""
    if api_version is None or api_version.strip() not in SUPPORTED_API_VERSIONS:
        raise UnsupportedApiVersionError()


async def answer_unsupported_api_version(request: Request, error: UnsupportedApiVersionError) -> JSONResponse:
    """Answer 400 unsupported_api_version naming the header and the versions to send, never echoing what was sent."""
    message = f"send the {API_VERSION_HEADER} header with one of: {', '.join(SUPPORTED_API_VERSIONS)}"
    error_body = RenderError(code=RenderErrorCode.UNSUPPORTED_API_VERSION, message=message)
    return JSONResponse(error_body.model_dump(mode="json"), status_code=HTTP_400_BAD_REQUEST)
