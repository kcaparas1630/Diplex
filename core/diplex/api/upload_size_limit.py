"""Answers 413 to a request whose body is over the upload limit, before the route gets to use it."""

from starlette.datastructures import Headers
from starlette.status import HTTP_413_CONTENT_TOO_LARGE
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from diplex.definition import RenderError, RenderErrorCode


class _UploadTooLargeError(Exception):
    """Stops the app reading a body that has gone over the limit."""


class UploadSizeLimit:
    """ASGI middleware that refuses a body over `max_upload_bytes`, by its Content-Length or as it arrives."""

    def __init__(self, app: ASGIApp, max_upload_bytes: int) -> None:
        """Wrap the app with the limit in bytes."""
        self.app = app
        self.max_upload_bytes = max_upload_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request on, answering 413 instead of the app's response once the body is over the limit."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared_length = Headers(scope=scope).get("content-length", "")
        if declared_length.isdecimal() and int(declared_length) > self.max_upload_bytes:
            await self._send_too_large(send)
            return

        received_bytes = 0
        over_limit = False
        refusal_sent = False

        async def counting_receive() -> Message:
            """Receive the next piece of the body, raising once the total is over the limit."""
            nonlocal received_bytes, over_limit
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_upload_bytes:
                    over_limit = True
                    raise _UploadTooLargeError()
            return message

        async def guarded_send(message: Message) -> None:
            """Send the app's response, or the 413 in its place once the body went over the limit."""
            nonlocal refusal_sent
            if not over_limit:
                await send(message)
            elif not refusal_sent:
                refusal_sent = True
                await self._send_too_large(send)

        try:
            await self.app(scope, counting_receive, guarded_send)
        except Exception:
            if not over_limit:
                raise  # once over the limit, any error is the app giving up on the body; the 413 stands
        if over_limit and not refusal_sent:
            await self._send_too_large(send)

    async def _send_too_large(self, send: Send) -> None:
        """Send the 413 response with the limit in its message."""
        error_body = RenderError(
            code=RenderErrorCode.UPLOAD_TOO_LARGE,
            message=f"the upload is over the engine's limit of {self.max_upload_bytes:,} bytes",
        ).model_dump_json()
        await send(
            {
                "type": "http.response.start",
                "status": HTTP_413_CONTENT_TOO_LARGE,
                "headers": [(b"content-type", b"application/json"), (b"connection", b"close")],
            }
        )
        await send({"type": "http.response.body", "body": error_body.encode()})
