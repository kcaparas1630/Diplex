"""Formats the smoke test's results as a Markdown table, with totals, to post on an issue."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class SampleRow(Protocol):
    """The fields of one sample's result that the table shows (render_request.SampleResult has them)."""

    sample_name: str
    size_bytes: int
    status: int
    outcome: str
    page_count: int | None
    image_bytes: int
    pdf_bytes: int | None
    seconds: float


TABLE_HEADER = (
    "| Sample | Size | Status | Outcome | Pages | Images | PDF part | Time |\n"
    "|---|--:|--:|---|--:|--:|--:|--:|\n"
)


def format_results_table(results: Sequence[SampleRow]) -> str:
    """Return one row per sample and a line of totals."""
    rows = [
        f"| {result.sample_name} | {_kilobytes(result.size_bytes)} | {result.status} | {result.outcome} | "
        f"{'-' if result.page_count is None else result.page_count} | {_kilobytes(result.image_bytes)} | "
        f"{'-' if result.pdf_bytes is None else _kilobytes(result.pdf_bytes)} | {result.seconds:.1f} s |\n"
        for result in results
    ]
    rendered = [result for result in results if result.outcome == "ok"]
    total_pages = sum(result.page_count or 0 for result in rendered)
    total_seconds = sum(result.seconds for result in results)
    totals = (
        f"\n{len(rendered)} of {len(results)} samples rendered, {total_pages} pages, "
        f"{total_seconds:.1f} s in all.\n"
    )
    return TABLE_HEADER + "".join(rows) + totals


def _kilobytes(byte_count: int) -> str:
    """Show a byte count in KB, rounded."""
    return f"{byte_count / 1000:,.0f} KB"
