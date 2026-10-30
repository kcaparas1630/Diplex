"""Convention rules for TypeScript files: file docblock, one-line comments, names and import boundaries."""

from __future__ import annotations

from pathlib import Path

from ..report import Violation
from .comments import check_declaration_comments
from .declarations import find_declarations
from .docblock import check_file_docblock
from .imports import check_imports
from .names import check_names

__all__ = ["check_typescript_file"]


def check_typescript_file(repository_root: Path, path: Path, is_test: bool) -> list[Violation]:
    """Read one TypeScript file and run every TypeScript rule on it; tests skip the import rule."""
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    declarations = find_declarations(lines)
    violations = (
        check_file_docblock(path, lines)
        + check_declaration_comments(path, lines, declarations)
        + check_names(path, lines, declarations)
    )
    if not is_test:
        violations += check_imports(repository_root, path, source)
    return violations
