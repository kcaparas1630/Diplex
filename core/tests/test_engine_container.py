"""Tests a running engine container over HTTP; set DIPLEX_ENGINE_URL (e.g. http://127.0.0.1:8000) to run them."""

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest

ENGINE_URL = os.environ.get("DIPLEX_ENGINE_URL", "").rstrip("/")
ENGINE_API_KEY = os.environ.get("DIPLEX_API_KEY", "").strip()  # the container's key, when it was started with one
SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
UNOSERVER_START_SECONDS = 60  # a DOCX waits for LibreOffice to start, but can still get 503 (a busy pool, or no wait set)

pytestmark = pytest.mark.skipif(not ENGINE_URL, reason="DIPLEX_ENGINE_URL is not set to a running engine container")


def _sample_bytes(sample_name: str) -> bytes:
    """Read a sample, skipping the test when it isn't in samples/."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")
    return sample_path.read_bytes()


def _post_render(document_bytes: bytes) -> tuple[int, str, bytes]:
    """POST the bytes to /render as the document part, with DIPLEX_API_KEY if set; return the status, content type and body."""
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="upload"\r\n\r\n'.encode()
        + document_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Diplex-Api-Version": "1"}
    if ENGINE_API_KEY:
        headers["Authorization"] = f"Bearer {ENGINE_API_KEY}"
    request = urllib.request.Request(f"{ENGINE_URL}/render", data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.status, response.headers["Content-Type"], response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers["Content-Type"], error.read()


def _part_names(content_type: str, body: bytes) -> list[str]:
    """The names of a multipart/form-data body's parts, in order."""
    message = BytesParser(policy=policy.HTTP).parsebytes(f"Content-Type: {content_type}\r\n\r\n".encode() + body)
    return [part.get_param("name", header="content-disposition") for part in message.iter_parts()]


def test_health_answers():
    """GET /health is 200 {"status": "ok"}."""
    with urllib.request.urlopen(f"{ENGINE_URL}/health", timeout=10) as response:
        assert (response.status, json.load(response)) == (200, {"status": "ok"})


def test_a_pdf_renders():
    """The IRS form comes back as its manifest and two page images."""
    status, content_type, body = _post_render(_sample_bytes("irs-form-1040-2025.pdf"))

    assert status == 200
    assert _part_names(content_type, body) == ["manifest", "page", "page"]


def test_a_docx_renders_through_the_containers_unoserver():
    """A DOCX is converted by the unoserver pool inside the container, retrying any 503 while LibreOffice starts."""
    docx_bytes = _sample_bytes("poi-comments.docx")
    deadline = time.monotonic() + UNOSERVER_START_SECONDS
    status, content_type, body = _post_render(docx_bytes)
    while status == 503 and time.monotonic() < deadline:
        time.sleep(1)
        status, content_type, body = _post_render(docx_bytes)

    assert status == 200
    part_names = _part_names(content_type, body)
    assert part_names[0] == "manifest" and part_names[-1] == "pdf"
    assert set(part_names[1:-1]) == {"page"}
