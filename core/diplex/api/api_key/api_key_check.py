"""Checks the optional static API key on /render (ADR 012): with DIPLEX_API_KEY set, the request must send it as a Bearer token."""

import hmac
from typing import Annotated

from fastapi import Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED

from diplex.definition import RenderError, RenderErrorCode

API_KEY_SCHEME_NAME = "ApiKey"
UNAUTHORIZED_MESSAGE = "send the engine's API key as `Authorization: Bearer <key>`"
bearer_scheme = HTTPBearer(
    scheme_name=API_KEY_SCHEME_NAME,
    description="The engine's DIPLEX_API_KEY. Only needed when the engine is started with one.",
    auto_error=False,  # a missing key is answered by answer_rejected_api_key, with the contract's error body
)


class ApiKeyRejectedError(Exception):
    """The engine has an API key and the request didn't send it."""


def require_api_key(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)]
) -> None:
    """Let the request through when the engine has no key or the request sent it; raise ApiKeyRejectedError otherwise."""
    expected_key = request.app.state.api_key
    if expected_key is None:
        return
    sent_key = credentials.credentials if credentials is not None else ""
    if not hmac.compare_digest(sent_key.encode(), expected_key.encode()):  # takes as long whatever was sent
        raise ApiKeyRejectedError()


async def answer_rejected_api_key(request: Request, error: ApiKeyRejectedError) -> JSONResponse:
    """Answer 401 unauthorized with the contract's error body and the challenge RFC 6750 §3 asks for."""
    error_body = RenderError(code=RenderErrorCode.UNAUTHORIZED, message=UNAUTHORIZED_MESSAGE)
    return JSONResponse(
        error_body.model_dump(mode="json"), status_code=HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Bearer"}
    )
