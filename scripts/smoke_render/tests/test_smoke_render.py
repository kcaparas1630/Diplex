"""Tests the smoke test against a stand-in engine on localhost that answers like /render; no documents are made."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from scripts.smoke_render import SampleResult, format_results_table, post_document, render_samples

BOUNDARY = "stand-in-boundary"


def _form_data(parts: list[tuple[str, str | None, bytes]]) -> bytes:
    """Build a multipart/form-data body from (name, file name, bytes) parts."""
    pieces = []
    for part_name, file_name, part_bytes in parts:
        disposition = f'form-data; name="{part_name}"' + (f'; filename="{file_name}"' if file_name else "")
        pieces.append(f"--{BOUNDARY}\r\nContent-Disposition: {disposition}\r\n\r\n".encode() + part_bytes + b"\r\n")
    return b"".join(pieces) + f"--{BOUNDARY}--\r\n".encode()


class StandInEngine(BaseHTTPRequestHandler):
    """Answers /render by what the upload starts with: %PDF two pages, PK a page and a PDF, anything else 415."""

    unavailable_answers_left = 0
    received_headers: list[dict[str, str]] = []

    def do_POST(self) -> None:
        """Read the upload and answer as the engine would."""
        StandInEngine.received_headers.append(dict(self.headers))
        upload = self.rfile.read(int(self.headers["Content-Length"]))
        document_bytes = upload.split(b"\r\n\r\n", 1)[1]
        manifest_pages = [{"index": 1, "width": 612.0, "height": 792.0}]
        if document_bytes.startswith(b"PK") and StandInEngine.unavailable_answers_left > 0:
            StandInEngine.unavailable_answers_left -= 1
            self._answer(503, "application/json", json.dumps({"code": "converter_unavailable", "message": "starting"}).encode())
        elif document_bytes.startswith(b"%PDF"):
            manifest_pages.append({"index": 2, "width": 612.0, "height": 792.0})
            parts = [("manifest", None, json.dumps({"pages": manifest_pages}).encode()), ("page", "page-0001.webp", b"W" * 1000), ("page", "page-0002.webp", b"W" * 1000)]
            self._answer(200, f"multipart/form-data; boundary={BOUNDARY}", _form_data(parts))
        elif document_bytes.startswith(b"PK"):
            parts = [("manifest", None, json.dumps({"pages": manifest_pages}).encode()), ("page", "page-0001.webp", b"W" * 3000), ("pdf", "document.pdf", b"%PDF" + b"P" * 2000)]
            self._answer(200, f"multipart/form-data; boundary={BOUNDARY}", _form_data(parts))
        else:
            self._answer(415, "application/json", json.dumps({"code": "unsupported_document_type", "message": "no"}).encode())

    def log_message(self, *_) -> None:
        """Keep the stand-in quiet."""

    def _answer(self, status: int, content_type: str, body: bytes) -> None:
        """Send one response."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def engine_url() -> Iterator[str]:
    """Run the stand-in engine on a free localhost port for one test."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), StandInEngine)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def samples_folder(tmp_path: Path) -> Path:
    """A folder of stand-in files named like samples: a PDF, a DOCX, a renamed text file, and a file that's skipped."""
    (tmp_path / "a-report.pdf").write_bytes(b"%PDF-1.7 stand-in")
    (tmp_path / "b-letter.docx").write_bytes(b"PK stand-in")
    (tmp_path / "c-renamed.pdf").write_bytes(b"plain text")
    (tmp_path / "SOURCES.md").write_text("not a sample")
    return tmp_path


def test_every_docx_and_pdf_is_rendered_and_summarised(engine_url, samples_folder):
    """Each sample gets its status, outcome, page count, image and PDF sizes; other files are skipped."""
    reported = []

    results = render_samples(engine_url, samples_folder, on_result=reported.append)

    assert reported == results
    assert [(result.sample_name, result.status, result.outcome, result.page_count) for result in results] == [
        ("a-report.pdf", 200, "ok", 2),
        ("b-letter.docx", 200, "ok", 1),
        ("c-renamed.pdf", 415, "unsupported_document_type", None),
    ]
    assert [(result.image_bytes, result.pdf_bytes) for result in results] == [(2000, None), (3000, 2004), (0, None)]


def test_a_docx_is_retried_while_unoserver_starts(engine_url, samples_folder, monkeypatch):
    """A 503 while LibreOffice starts is asked again, so the sample is reported by what it really does."""
    monkeypatch.setattr(StandInEngine, "unavailable_answers_left", 2)
    monkeypatch.setattr("scripts.smoke_render.render_request.time.sleep", lambda seconds: None)

    results = render_samples(engine_url, samples_folder, on_result=lambda result: None)

    assert results[1].outcome == "ok"
    assert StandInEngine.unavailable_answers_left == 0


def test_the_table_has_a_row_per_sample_and_the_totals():
    """The Markdown table shows each sample and a line counting what rendered."""
    results = [
        SampleResult("report.pdf", 220_237, 200, "ok", 2, 254_008, None, 0.5),
        SampleResult("broken.docx", 18_000, 422, "docx_conversion_failed", None, 0, None, 0.2),
    ]

    table = format_results_table(results)

    assert "| report.pdf | 220 KB | 200 | ok | 2 | 254 KB | - | 0.5 s |" in table
    assert "| broken.docx | 18 KB | 422 | docx_conversion_failed | - | 0 KB | - | 0.2 s |" in table
    assert table.endswith("1 of 2 samples rendered, 2 pages, 0.7 s in all.\n")


@pytest.mark.parametrize(("configured_key", "expected_authorization"), [("engine-key-0123456789", "Bearer engine-key-0123456789"), ("", None)])
def test_the_engine_key_is_sent_when_set(engine_url, monkeypatch, configured_key, expected_authorization):
    """With DIPLEX_API_KEY set, every upload carries it as a Bearer token; without it, no Authorization header."""
    monkeypatch.setenv("DIPLEX_API_KEY", configured_key)
    StandInEngine.received_headers.clear()

    post_document(engine_url, b"%PDF-1.7 stand-in")

    assert StandInEngine.received_headers[0].get("Authorization") == expected_authorization
