"""Load test: sends every DOCX sample to a running engine's /render, several at once, and reports throughput and latency.

Run it with `python -m scripts.load_test http://127.0.0.1:8000 --concurrency 8`; it needs only the standard library.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .container_memory import PeakMemorySampler, parse_memory_usage, read_container_memory
from .load_report import format_load_report, percentile
from .timed_render import TimedRender, time_render

__all__ = [
    "PeakMemorySampler",
    "TimedRender",
    "format_load_report",
    "parse_memory_usage",
    "percentile",
    "read_container_memory",
    "run_load_test",
    "time_render",
]


def run_load_test(
    engine_url: str,
    sample_paths: Sequence[Path],
    concurrency: int,
    rounds: int,
    on_render: Callable[[TimedRender], None],
) -> tuple[list[TimedRender], float]:
    """Render every sample `rounds` times, `concurrency` at a time; return the renders and the wall time in seconds."""
    queued_paths = [sample_path for _ in range(rounds) for sample_path in sample_paths]
    renders: list[TimedRender] = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        pending_renders = [executor.submit(time_render, engine_url, sample_path) for sample_path in queued_paths]
        for finished_render in as_completed(pending_renders):
            timed_render = finished_render.result()
            on_render(timed_render)
            renders.append(timed_render)
    return renders, time.perf_counter() - started
