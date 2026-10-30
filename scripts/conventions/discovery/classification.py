"""Decides whether a source file is a test, since tests are exempt from the import and folder rules."""

from __future__ import annotations

from pathlib import Path

from ..settings import TEST_FOLDER_NAMES


def is_test_file(repository_root: Path, path: Path) -> bool:
    """Tell whether `path` is a test file or lives in a test folder."""
    folder_parts = path.relative_to(repository_root).parts[:-1]
    if any(part in TEST_FOLDER_NAMES for part in folder_parts):
        return True
    name = path.name
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
        or ".test." in name
        or ".spec." in name
    )
