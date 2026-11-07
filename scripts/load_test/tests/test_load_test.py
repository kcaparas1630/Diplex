"""Tests the load test against a stand-in engine on localhost, and its report and memory sampling; no documents are made."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from scripts.load_test import (
    PeakMemorySampler,
    TimedRender,
    format_load_report,
    parse_memory_usage,
    percentile,
    run_load_test,
    time_render,
)

STAND_IN_RENDER_SECONDS = 0.2


class StandInEngine(BaseHTTPRequestHandler):
    """Answers /render after a moment, counting renders in flight: 200 for PK uploads, 503 converter_busy for busy ones."""

    in_flight = 0
    most_in_flight = 0
    lock = threading.Lock()

    def do_POST(self) -> None:
        """Read the upload, hold it for a moment, and answer as the engine would."""
        upload = self.rfile.read(int(self.headers["Content-Length"]))
        with StandInEngine.lock:
            StandInEngine.in_flight += 1
            StandInEngine.most_in_flight = max(StandInEngine.most_in_flight, StandInEngine.in_flight)
        time.sleep(STAND_IN_RENDER_SECONDS)
        with StandInEngine.lock:
            StandInEngine.in_flight -= 1
        if b"busy" in upload:
            self._answer(503, "application/json", json.dumps({"code": "converter_busy", "message": "busy"}).encode())
        else:
            self._answer(200, "multipart/form-data; boundary=stand-in", b"--stand-in--\r\n")

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
    StandInEngine.in_flight = StandInEngine.most_in_flight = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), StandInEngine)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def sample_paths(tmp_path: Path) -> list[Path]:
    """Three stand-in files named like DOCX samples."""
    paths = [tmp_path / f"sample-{number}.docx" for number in range(3)]
    for path in paths:
        path.write_bytes(b"PK stand-in")
    return paths


def test_every_sample_is_rendered_once_per_round_with_the_given_concurrency(engine_url, sample_paths):
    """Three samples, two rounds, two at a time: six renders, never more than two in flight."""
    seen_renders = []

    renders, wall_seconds = run_load_test(engine_url, sample_paths, concurrency=2, rounds=2, on_render=seen_renders.append)

    assert len(renders) == 6 and renders == seen_renders
    assert sorted(render.sample_name for render in renders) == sorted([path.name for path in sample_paths] * 2)
    assert all(render.outcome == "ok" and render.status == 200 for render in renders)
    assert StandInEngine.most_in_flight == 2
    assert wall_seconds >= 3 * STAND_IN_RENDER_SECONDS  # six renders, two at a time


def test_an_error_answer_is_recorded_by_its_code_without_retrying(engine_url, tmp_path):
    """A 503 is not retried during the load test; it counts as a render with the engine's code."""
    sample_path = tmp_path / "busy.docx"
    sample_path.write_bytes(b"PK busy")

    timed_render = time_render(engine_url, sample_path)

    assert (timed_render.status, timed_render.outcome) == (503, "converter_busy")
    assert timed_render.seconds >= STAND_IN_RENDER_SECONDS


def test_percentiles_are_nearest_rank():
    """p50 of 1..10 is 5, p95 and p99 are 10, and p100 is the largest."""
    values = [float(value) for value in range(1, 11)]

    assert [percentile(values, percent) for percent in (50, 95, 99, 100)] == [5.0, 10.0, 10.0, 10.0]
    with pytest.raises(ValueError):
        percentile([], 50)


def test_the_report_counts_outcomes_and_times_only_successful_renders():
    """Throughput and latency use the successful renders; every outcome is counted; the slowest are listed."""
    renders = [TimedRender(f"doc-{number}.docx", 200, "ok", float(number)) for number in range(1, 5)] + [
        TimedRender("stuck.docx", 422, "docx_conversion_failed", 120.0)
    ]

    report = format_load_report(renders, wall_seconds=60.0, concurrency=4, peak_memory_bytes=3 * 1024**3)

    assert "| 4 | 5 | 4 | 60.0 s | 4.0 docs/min | 2.00 s | 4.00 s | 4.00 s | 4.00 s | 3.00 GiB |" in report
    assert "| ok | 4 |" in report and "| docx_conversion_failed | 1 |" in report
    assert report.index("| stuck.docx | 422 | docx_conversion_failed | 120.00 s |") < report.index("| doc-4.docx |")


def test_the_report_says_when_memory_was_not_measured():
    """Without a container to sample, the memory column says so."""
    report = format_load_report([TimedRender("a.docx", 200, "ok", 1.0)], wall_seconds=1.0, concurrency=1, peak_memory_bytes=None)

    assert "| not measured |" in report


@pytest.mark.parametrize(
    ("memory_usage", "expected_bytes"),
    [("1.5GiB / 15.6GiB", 1610612736), ("512MiB / 2GiB", 536870912), ("800kB / 1GB", 800000), ("0B / 0B", 0), ("--", None)],
)
def test_docker_stats_memory_is_read_in_bytes(memory_usage, expected_bytes):
    """docker stats' MemUsage is read with binary and decimal units; anything else gives None."""
    assert parse_memory_usage(memory_usage) == expected_bytes


def test_the_sampler_keeps_the_highest_reading():
    """Readings that rise and fall leave the peak; unreadable ones are skipped."""
    readings = iter([100, None, 300, 200])
    sampler = PeakMemorySampler(lambda: next(readings, 200), interval_seconds=0.01)

    sampler.start()
    time.sleep(0.1)
    peak_bytes = sampler.stop()

    assert peak_bytes == 300
