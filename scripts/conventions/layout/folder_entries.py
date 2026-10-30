"""Folder entry rule: every folder of code has an entry file whose docblock says what the folder contains."""

from __future__ import annotations

from collections import defaultdict
from fnmatch import fnmatch
from pathlib import Path

from ..report import Violation
from ..settings import CONFIG_FILE_PATTERNS, PYTHON_ENTRY_NAME, TYPESCRIPT_ENTRY_NAMES, TYPESCRIPT_SUFFIXES


def check_folder_entries(repository_root: Path, source_files: list[Path]) -> list[Violation]:
    """Return a violation for each folder of code below the repository root that has no entry file."""
    files_by_folder: dict[Path, list[Path]] = defaultdict(list)
    for path in source_files:
        if path.parent != repository_root:
            files_by_folder[path.parent].append(path)
    violations: list[Violation] = []
    for folder, folder_files in sorted(files_by_folder.items()):
        code_files = [path for path in folder_files if not _is_config_file(path)]
        file_names = {path.name for path in folder_files}
        has_python = any(path.suffix == ".py" for path in code_files)
        has_typescript = any(path.suffix in TYPESCRIPT_SUFFIXES for path in code_files)
        if has_python and PYTHON_ENTRY_NAME not in file_names:
            violations.append(_missing_entry(folder, PYTHON_ENTRY_NAME))
        if has_typescript and not file_names & TYPESCRIPT_ENTRY_NAMES:
            violations.append(_missing_entry(folder, "index.ts"))
    return violations


def _is_config_file(path: Path) -> bool:
    """Tell whether a file is tool configuration rather than code of the folder."""
    return any(fnmatch(path.name, pattern) for pattern in CONFIG_FILE_PATTERNS)


def _missing_entry(folder: Path, entry_name: str) -> Violation:
    """Build the violation for a folder that lacks its entry file."""
    message = f"folder has code but no `{entry_name}`; add one whose docblock says what this folder contains"
    return Violation(folder / entry_name, 1, "folder-entry", message)
