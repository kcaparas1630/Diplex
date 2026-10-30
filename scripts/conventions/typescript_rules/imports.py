"""Import rule for TypeScript: every relative import must respect the folder boundaries.

Package imports (`@diplex/store`, `zod`) go through a package's own entry and are always allowed.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..boundaries import import_problem
from ..report import Violation
from .module_resolution import resolve_specifier

RELATIVE_SPECIFIER = r"""['"](\.{1,2}(?:/[^'"]*)?)['"]"""
IMPORT_PATTERNS = (
    re.compile(r"\bfrom\s+" + RELATIVE_SPECIFIER),
    re.compile(r"\bimport\s+" + RELATIVE_SPECIFIER),
    re.compile(r"\b(?:require|import)\(\s*" + RELATIVE_SPECIFIER + r"\s*\)"),
)


def check_imports(repository_root: Path, path: Path, source: str) -> list[Violation]:
    """Return a violation for every relative import that crosses a forbidden folder boundary."""
    violations: list[Violation] = []
    for pattern in IMPORT_PATTERNS:
        for found in pattern.finditer(source):
            target = resolve_specifier(path, found.group(1))
            if target is None:
                continue
            problem = import_problem(path, target)
            if problem:
                line = source.count("\n", 0, found.start()) + 1
                shown = target.relative_to(repository_root).as_posix()
                violations.append(Violation(path, line, "import-boundary", f"`{shown}`: {problem}"))
    return violations
