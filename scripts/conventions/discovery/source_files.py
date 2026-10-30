"""Walks the repository and lists the Python and TypeScript files the convention rules apply to."""

from __future__ import annotations

import os
from pathlib import Path

from ..settings import EXCLUDED_DIRECTORIES, GENERATED_FILE_SUFFIXES, PYTHON_SUFFIXES, TYPESCRIPT_SUFFIXES


def find_source_files(repository_root: Path) -> list[Path]:
    """Return every Python and TypeScript file under the root, skipping excluded, hidden and generated files."""
    source_suffixes = PYTHON_SUFFIXES | TYPESCRIPT_SUFFIXES
    found: list[Path] = []
    for directory, folder_names, file_names in os.walk(repository_root):
        folder_names[:] = sorted(
            name for name in folder_names if name not in EXCLUDED_DIRECTORIES and not name.startswith(".")
        )
        for file_name in sorted(file_names):
            path = Path(directory, file_name).resolve()
            if path.suffix in source_suffixes and not file_name.endswith(GENERATED_FILE_SUFFIXES):
                found.append(path)
    return found
