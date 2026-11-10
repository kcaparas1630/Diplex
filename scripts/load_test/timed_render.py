"""Sends one sample to a running engine's /render and times it, keeping only the status and the outcome."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from scripts.smoke_render import post_document


@dataclass(frozen=True)
class TimedRender:
    """One render in the load test: which sample, what the engine answered, and how long the request took."""

    sample_name: str
    status: int
    outcome: str  # ok, or the error code from the engine
    seconds: float


def time_render(engine_url: str, sample_path: Path) -> TimedRender:
    """POST the sample to /render once, without retrying, and time the whole request."""
    document_bytes = sample_path.read_bytes()
    started = time.perf_counter()
    status, content_type, body = post_document(engine_url, document_bytes)
    seconds = time.perf_counter() - started
    return TimedRender(sample_path.name, status, _outcome(status, content_type, body), seconds)


def _outcome(status: int, content_type: str, body: bytes) -> str:
    """ok for a 200, else the error code in the engine's JSON body, or unknown."""
    if status == 200:
        return "ok"
    if content_type.startswith("application/json"):
        try:
            return json.loads(body).get("code", "unknown")
        except ValueError:
            return "unknown"
    return "unknown"
