"""File name rule: names like utils or helpers invite unrelated code into one file."""

from __future__ import annotations

from pathlib import Path

from ..report import Violation
from ..settings import VAGUE_FILE_STEMS


def check_file_name(path: Path) -> list[Violation]:
    """Return a violation when a file's name does not say what the file is responsible for."""
    stem = path.name.split(".")[0].lower()
    if stem not in VAGUE_FILE_STEMS:
        return []
    message = f"`{path.name}` does not say what the file does; name it after its one responsibility"
    return [Violation(path, 1, "unclear-file-name", message)]
