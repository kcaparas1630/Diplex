"""Naming rules for Python: flags vague or cryptic names wherever a file defines a name."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ..naming import name_problem
from ..report import Violation


def check_names(path: Path, tree: ast.Module) -> list[Violation]:
    """Return one violation for each unclear name, at the first place the file defines it."""
    violations: list[Violation] = []
    reported: set[str] = set()
    for line, name in _defined_names(tree):
        if name in reported:
            continue
        problem = name_problem(name)
        if problem:
            reported.add(name)
            violations.append(Violation(path, line, "unclear-name", problem))
    return violations


def _defined_names(tree: ast.Module) -> Iterator[tuple[int, str]]:
    """Yield the line and name of every function, class, parameter, variable and attribute the file defines."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield node.lineno, node.name
        elif isinstance(node, ast.arg):
            yield node.lineno, node.arg
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            yield node.lineno, node.id
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            yield node.lineno, node.attr
        elif isinstance(node, ast.ExceptHandler) and node.name:
            yield node.lineno, node.name
