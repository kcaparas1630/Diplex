"""Convention checker: verifies the repository's code against docs/code-convention 007 to 010.

Walks the repository, runs the Python or TypeScript rules on every source file and the layout
rules on every folder, and returns what it found. Run it with `python -m scripts.conventions`.
"""

from __future__ import annotations

from pathlib import Path

from .discovery import find_source_files, is_test_file
from .layout import check_layout
from .python_rules import check_python_file
from .report import Violation, format_report
from .typescript_rules import check_typescript_file

__all__ = ["Violation", "check_repository", "format_report"]


def check_repository(repository_root: Path) -> list[Violation]:
    """Check every source file and folder under the repository root and return all violations."""
    repository_root = repository_root.resolve()
    source_files = find_source_files(repository_root)
    violations = check_layout(repository_root, source_files)
    for path in source_files:
        is_test = is_test_file(repository_root, path)
        if path.suffix == ".py":
            violations += check_python_file(repository_root, path, is_test)
        else:
            violations += check_typescript_file(repository_root, path, is_test)
    return sorted(violations, key=lambda found: (str(found.path), found.line, found.rule))
