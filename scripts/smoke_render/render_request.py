"""Sends one sample to a running engine's /render and reads what came back, using only the standard library."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path

UNOSERVER_START_SECONDS = 60  # a DOCX waits for LibreOffice to start but can still get 503; keep asking for this long
REQUEST_TIMEOUT_SECONDS = 600
API_VERSION = "1"  # the engine API version these scripts code against (ADR 012)


@dataclass(frozen=True)
class SampleResult:
    """What one sample's render gave: the HTTP status, the outcome, the pages, the PDF part and the time it took."""

    sample_name: str
    size_bytes: int
    status: int
    outcome: str  # ok, or the error code from the engine
    page_count: int | None
    image_bytes: int
    pdf_bytes: int | None
    seconds: float


def render_sample(engine_url: str, sample_path: Path) -> SampleResult:
    """Render one sample through the engine, waiting out 503 while unoserver starts, and summarise the answer."""
    document_bytes = sample_path.read_bytes()
    deadline = time.monotonic() + UNOSERVER_START_SECONDS
    while True:
        started = time.perf_counter()
        status, content_type, body = post_document(engine_url, document_bytes)
        seconds = time.perf_counter() - started
        if status != 503 or time.monotonic() > deadline:
            break
        time.sleep(1)
    if status != 200:
        outcome = json.loads(body).get("code", "unknown") if content_type.startswith("application/json") else "unknown"
        return SampleResult(sample_path.name, len(document_bytes), status, outcome, None, 0, None, seconds)
    parts = _parse_parts(content_type, body)
    page_images = [part_bytes for part_name, part_bytes in parts if part_name == "page"]
    manifest = json.loads(next(part_bytes for part_name, part_bytes in parts if part_name == "manifest"))
    pdf_part = next((part_bytes for part_name, part_bytes in parts if part_name == "pdf"), None)
    if len(manifest["pages"]) != len(page_images):
        raise ValueError(f"{sample_path.name}: {len(manifest['pages'])} pages in the manifest, {len(page_images)} images")
    return SampleResult(
        sample_name=sample_path.name,
        size_bytes=len(document_bytes),
        status=status,
        outcome="ok",
        page_count=len(page_images),
        image_bytes=sum(len(image) for image in page_images),
        pdf_bytes=None if pdf_part is None else len(pdf_part),
        seconds=seconds,
    )


def post_document(engine_url: str, document_bytes: bytes) -> tuple[int, str, bytes]:
    """POST the bytes as an upload, with the API version and DIPLEX_API_KEY if set; return status, content type and body."""
    boundary = uuid.uuid4().hex
    request_body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="upload"\r\n\r\n'.encode()
        + document_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Diplex-Api-Version": API_VERSION}
    api_key = os.environ.get("DIPLEX_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"  # the engine's key, when it was started with one (ADR 012)
    request = urllib.request.Request(f"{engine_url.rstrip('/')}/render", data=request_body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.status, response.headers["Content-Type"], response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


def _parse_parts(content_type: str, body: bytes) -> list[tuple[str, bytes]]:
    """Split a multipart/form-data body into (part name, bytes) pairs, in order."""
    message = BytesParser(policy=policy.HTTP).parsebytes(f"Content-Type: {content_type}\r\n\r\n".encode() + body)
    return [
        (part.get_param("name", header="content-disposition"), part.get_payload(decode=True))
        for part in message.iter_parts()
    ]
