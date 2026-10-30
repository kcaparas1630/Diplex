"""Convention rules for Python files: docstrings, names and import boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

from ..report import Violation
from .docstrings import check_docstrings
from .imports import check_imports
from .names import check_names

__all__ = ["check_python_file"]


def check_python_file(repository_root: Path, path: Path, is_test: bool) -> list[Violation]:
    """Parse one Python file and run every Python rule on it; tests skip the import rule."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        return [Violation(path, error.lineno or 1, "syntax-error", f"cannot parse the file: {error.msg}")]
    violations = check_docstrings(path, tree) + check_names(path, tree)
    if not is_test:
        violations += check_imports(repository_root, path, tree)
    return violations
