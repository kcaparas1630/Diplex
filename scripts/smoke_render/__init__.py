"""Smoke test: renders every sample through a running engine's /render and reports what happened.

Run it with `python -m scripts.smoke_render http://127.0.0.1:8000`; it needs only the standard library.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .render_request import SampleResult, post_document, render_sample
from .results_table import format_results_table

__all__ = ["SampleResult", "format_results_table", "post_document", "render_sample", "render_samples"]

SAMPLE_SUFFIXES = (".docx", ".pdf")


def render_samples(engine_url: str, samples_folder: Path, on_result: Callable[[SampleResult], None]) -> list[SampleResult]:
    """Render every DOCX and PDF in the folder, by name, calling on_result after each one."""
    sample_paths = sorted(path for path in samples_folder.iterdir() if path.suffix.lower() in SAMPLE_SUFFIXES)
    results = []
    for sample_path in sample_paths:
        result = render_sample(engine_url, sample_path)
        on_result(result)
        results.append(result)
    return results
