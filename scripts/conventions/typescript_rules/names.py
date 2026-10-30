"""Naming rules for TypeScript: flags vague or cryptic names in declarations and variables."""

from __future__ import annotations

from pathlib import Path

from ..naming import name_problem
from ..report import Violation
from .declarations import Declaration, find_variable_names


def check_names(path: Path, lines: list[str], declarations: list[Declaration]) -> list[Violation]:
    """Return one violation for each unclear name, at the first line that declares it."""
    named = [(declaration.line, declaration.name) for declaration in declarations] + find_variable_names(lines)
    violations: list[Violation] = []
    reported: set[str] = set()
    for line, name in sorted(named):
        if name in reported:
            continue
        problem = name_problem(name)
        if problem:
            reported.add(name)
            violations.append(Violation(path, line, "unclear-name", problem))
    return violations
