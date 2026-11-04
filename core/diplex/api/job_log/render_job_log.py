"""Logs one line per render job (ID, source type, size, page count, duration, outcome), never the document's contents."""

import logging
import time
import traceback
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

render_job_logger = logging.getLogger("diplex.render")
JOB_LINE_FORMAT = "render job=%s source=%s bytes=%d pages=%s duration_ms=%d outcome=%s"


@dataclass
class RenderJob:
    """What the log line says about one /render request, filled in as the job runs."""

    size_bytes: int
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_type: str = "unknown"  # docx or pdf once the type is known
    page_count: int | None = None
    outcome: str = "ok"  # or the RenderErrorCode the job answered with


@contextmanager
def logged_render_job(size_bytes: int) -> Iterator[RenderJob]:
    """Time a render job and log its line when it ends: INFO when rendered, WARNING when refused, ERROR when failed."""
    render_job = RenderJob(size_bytes=size_bytes)
    started = time.perf_counter()
    try:
        yield render_job
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000)
        page_count = "-" if render_job.page_count is None else render_job.page_count
        render_job_logger.log(
            _job_line_level(render_job.outcome),
            JOB_LINE_FORMAT,
            render_job.job_id,
            render_job.source_type,
            render_job.size_bytes,
            page_count,
            duration_ms,
            render_job.outcome,
        )


def log_unexpected_error(render_job: RenderJob, error: Exception) -> None:
    """Log an error's type and stack, but not its message, which can quote the document."""
    stack = "".join(traceback.format_tb(error.__traceback__))
    render_job_logger.error("render job=%s failed with %s\n%s", render_job.job_id, type(error).__name__, stack)


def send_job_logs_to_stderr() -> None:
    """Print job lines at INFO and above on stderr, next to uvicorn's own logs, adding the handler only once."""
    if render_job_logger.handlers:
        return
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    render_job_logger.addHandler(stderr_handler)
    render_job_logger.setLevel(logging.INFO)


def _job_line_level(outcome: str) -> int:
    """Pick the level for a job's line from its outcome."""
    if outcome == "ok":
        return logging.INFO
    if outcome == "internal_error":
        return logging.ERROR
    return logging.WARNING
