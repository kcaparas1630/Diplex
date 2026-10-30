"""Docstring rules for Python: every module explains itself, and every function and class does so in one line."""

from __future__ import annotations

import ast
from pathlib import Path

from ..report import Violation

DEFINITION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def check_docstrings(path: Path, tree: ast.Module) -> list[Violation]:
    """Return a violation for a missing module docstring and for each definition without a one-line docstring."""
    violations: list[Violation] = []
    if not (ast.get_docstring(tree) or "").strip():
        violations.append(Violation(path, 1, "file-docblock", "add a module docstring at the top saying what this file does"))
    for node in ast.walk(tree):
        if isinstance(node, DEFINITION_NODES):
            violations.extend(_check_definition(path, node))
    return violations


def _check_definition(path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[Violation]:
    """Check that one function or class has a docstring of exactly one line."""
    is_class = isinstance(node, ast.ClassDef)
    kind = "class" if is_class else "function"
    docstring = (ast.get_docstring(node) or "").strip()
    if not docstring:
        rule = "schema-comment" if is_class else "function-comment"
        purpose = "what it is and what it is for" if is_class else "what it does"
        return [Violation(path, node.lineno, rule, f"{kind} `{node.name}` needs a one-line docstring saying {purpose}")]
    if "\n" in docstring:
        return [Violation(path, node.lineno, "one-line-comment", f"{kind} `{node.name}` docstring must be a single line")]
    return []
