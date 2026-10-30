"""Convention rules for files and folders, independent of language: length, names and folder entries."""

from __future__ import annotations

from pathlib import Path

from ..discovery import is_test_file
from ..report import Violation
from .file_length import check_file_length
from .file_names import check_file_name
from .folder_entries import check_folder_entries

__all__ = ["check_layout"]


def check_layout(repository_root: Path, source_files: list[Path]) -> list[Violation]:
    """Run the file and folder rules over every source file that is not a test."""
    production_files = [path for path in source_files if not is_test_file(repository_root, path)]
    violations: list[Violation] = []
    for path in production_files:
        violations += check_file_length(path) + check_file_name(path)
    violations += check_folder_entries(repository_root, production_files)
    return violations
