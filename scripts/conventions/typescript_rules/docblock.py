"""File docblock rule for TypeScript: the file opens with a /** */ block saying what it does."""

from __future__ import annotations

from pathlib import Path

from ..report import Violation


def check_file_docblock(path: Path, lines: list[str]) -> list[Violation]:
    """Return a violation when the first meaningful line of the file is not a /** docblock."""
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#!"):
            continue
        if stripped.startswith("/**"):
            return []
        return [Violation(path, line_number, "file-docblock", "start the file with a /** */ docblock saying what this file does")]
    return [Violation(path, 1, "file-docblock", "the file is empty; add a /** */ docblock saying what it is for")]
