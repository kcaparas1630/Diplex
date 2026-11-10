"""Summarises a load test's renders (throughput, latency percentiles, outcomes, peak memory) as Markdown to post on an issue."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import Protocol

SLOWEST_RENDER_COUNT = 10


class RenderRow(Protocol):
    """The fields of one render that the report uses (timed_render.TimedRender has them)."""

    sample_name: str
    status: int
    outcome: str
    seconds: float


def percentile(sorted_values: Sequence[float], percent: float) -> float:
    """The nearest-rank percentile of values sorted from smallest to largest."""
    if not sorted_values:
        raise ValueError("no values")
    rank = max(1, math.ceil(percent / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def format_load_report(
    renders: Sequence[RenderRow], wall_seconds: float, concurrency: int, peak_memory_bytes: int | None
) -> str:
    """Return the summary table, the count of each outcome, and the slowest renders."""
    succeeded_seconds = sorted(render.seconds for render in renders if render.outcome == "ok")
    throughput = len(succeeded_seconds) / wall_seconds * 60 if wall_seconds > 0 else 0.0
    if succeeded_seconds:
        latencies = [f"{percentile(succeeded_seconds, percent):.2f} s" for percent in (50, 95, 99, 100)]
    else:
        latencies = ["-"] * 4
    memory = "not measured" if peak_memory_bytes is None else f"{peak_memory_bytes / 1024**3:.2f} GiB"
    summary = (
        "| Concurrency | Renders | OK | Wall time | Throughput | p50 | p95 | p99 | Max | Peak memory |\n"
        "|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|\n"
        f"| {concurrency} | {len(renders)} | {len(succeeded_seconds)} | {wall_seconds:.1f} s | "
        f"{throughput:.1f} docs/min | {' | '.join(latencies)} | {memory} |\n"
    )
    outcome_rows = "".join(f"| {outcome} | {count} |\n" for outcome, count in Counter(render.outcome for render in renders).most_common())
    slowest_rows = "".join(
        f"| {render.sample_name} | {render.status} | {render.outcome} | {render.seconds:.2f} s |\n"
        for render in sorted(renders, key=lambda render: render.seconds, reverse=True)[:SLOWEST_RENDER_COUNT]
    )
    return (
        summary
        + "\nLatency is over the successful renders; throughput counts successful renders per minute of wall time.\n"
        + "\n| Outcome | Renders |\n|---|--:|\n"
        + outcome_rows
        + "\n| Slowest | Status | Outcome | Time |\n|---|--:|---|--:|\n"
        + slowest_rows
    )
