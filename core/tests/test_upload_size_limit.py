"""Unit tests for the UploadSizeLimit middleware, on a small app with one route that reads the body."""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from diplex.api.upload_size_limit import UploadSizeLimit
from diplex.definition import RenderError, RenderErrorCode

LIMIT_BYTES = 1000


def _client_for_upload_app(received_sizes: list[int]) -> TestClient:
    """Make a client for an app whose /upload route records the size of each body it reads."""
    upload_app = FastAPI()

    @upload_app.post("/upload")
    async def receive_upload(request: Request) -> dict:
        """Read the body and record its size."""
        received_sizes.append(len(await request.body()))
        return {"received": True}

    upload_app.add_middleware(UploadSizeLimit, max_upload_bytes=LIMIT_BYTES)
    return TestClient(upload_app)


def _in_chunks(body: bytes, chunk_size: int = 100):
    """Yield the body in pieces, so it is sent chunked with no Content-Length."""
    for start in range(0, len(body), chunk_size):
        yield body[start : start + chunk_size]


def _assert_refused(response) -> None:
    """Check the response is the 413 with the contract's error body."""
    assert response.status_code == 413
    error = RenderError.model_validate_json(response.content)
    assert error.code is RenderErrorCode.UPLOAD_TOO_LARGE
    assert "1,000 bytes" in error.message


@pytest.mark.parametrize("body_size", [500, LIMIT_BYTES])
def test_a_body_up_to_the_limit_reaches_the_route(body_size):
    """A body under or exactly at the limit is handled as usual, sent whole or in chunks."""
    received_sizes = []
    client = _client_for_upload_app(received_sizes)

    whole_response = client.post("/upload", content=b"x" * body_size)
    chunked_response = client.post("/upload", content=_in_chunks(b"x" * body_size))

    assert (whole_response.status_code, chunked_response.status_code) == (200, 200)
    assert received_sizes == [body_size, body_size]


def test_a_declared_length_over_the_limit_is_refused_without_reading():
    """A Content-Length over the limit gets 413 straight away; the route never runs."""
    received_sizes = []

    response = _client_for_upload_app(received_sizes).post("/upload", content=b"x" * (LIMIT_BYTES + 1))

    _assert_refused(response)
    assert received_sizes == []


def test_a_chunked_body_over_the_limit_is_refused_as_it_arrives():
    """A body sent without a Content-Length is counted as it arrives and refused once past the limit."""
    received_sizes = []

    response = _client_for_upload_app(received_sizes).post("/upload", content=_in_chunks(b"x" * 3000))

    _assert_refused(response)
    assert received_sizes == []


def test_a_route_that_turns_the_cut_off_body_into_its_own_error_still_gives_413():
    """FastAPI answers 400 when it can't read a body; the middleware sends 413 in its place."""
    parsing_app = FastAPI()

    @parsing_app.post("/upload")
    async def answer_400_on_unreadable_body(request: Request) -> JSONResponse:
        """Read the body, answering 400 if it can't be read, as FastAPI does for forms."""
        try:
            await request.body()
        except Exception:
            return JSONResponse({"error": "could not read the body"}, status_code=400)
        return JSONResponse({"received": True})

    parsing_app.add_middleware(UploadSizeLimit, max_upload_bytes=LIMIT_BYTES)

    response = TestClient(parsing_app).post("/upload", content=_in_chunks(b"x" * 3000))

    _assert_refused(response)


def test_an_error_under_the_limit_is_left_alone():
    """The middleware doesn't hide the app's own failures on a body within the limit."""
    failing_app = FastAPI()

    @failing_app.post("/upload")
    async def read_then_fail(request: Request) -> dict:
        """Read the body, then fail."""
        await request.body()
        raise RuntimeError("the route failed")

    failing_app.add_middleware(UploadSizeLimit, max_upload_bytes=LIMIT_BYTES)

    response = TestClient(failing_app, raise_server_exceptions=False).post("/upload", content=_in_chunks(b"x" * 500))

    assert response.status_code == 500
