"""File length rule: a long file is the usual sign that it holds more than one responsibility."""

from __future__ import annotations

from pathlib import Path

from ..report import Violation
from ..settings import MAX_FILE_LINES


def check_file_length(path: Path) -> list[Violation]:
    """Return a violation when a file has more lines than the limit."""
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count <= MAX_FILE_LINES:
        return []
    message = f"{line_count} lines (limit {MAX_FILE_LINES}); split it so each file has one responsibility"
    return [Violation(path, 1, "file-length", message)]
