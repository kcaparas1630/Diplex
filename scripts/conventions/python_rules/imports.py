"""Import rule for Python: every import of a repository file must respect the folder boundaries."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ..boundaries import import_problem
from ..report import Violation
from .module_resolution import resolve_absolute, resolve_relative


def check_imports(repository_root: Path, path: Path, tree: ast.Module) -> list[Violation]:
    """Return a violation for every import that crosses a folder boundary the convention forbids."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        for line, target in _import_targets(repository_root, path, node):
            problem = import_problem(path, target)
            if problem:
                shown = target.relative_to(repository_root).as_posix()
                violations.append(Violation(path, line, "import-boundary", f"`{shown}`: {problem}"))
    return violations


def _import_targets(repository_root: Path, path: Path, node: ast.AST) -> Iterator[tuple[int, Path]]:
    """Yield the line and repository file for each module an import statement loads."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            target = resolve_absolute(repository_root, alias.name)
            if target:
                yield node.lineno, target
    elif isinstance(node, ast.ImportFrom):
        for alias in node.names:
            target = _from_import_target(repository_root, path, node, alias.name)
            if target:
                yield node.lineno, target


def _from_import_target(repository_root: Path, path: Path, node: ast.ImportFrom, imported_name: str) -> Path | None:
    """Resolve one name of a `from ... import name`: a submodule if one exists, otherwise the module itself."""
    module_name = node.module or ""
    submodule_name = f"{module_name}.{imported_name}" if module_name else imported_name
    if node.level:
        return resolve_relative(path, node.level, submodule_name) or resolve_relative(path, node.level, module_name)
    return resolve_absolute(repository_root, submodule_name) or resolve_absolute(repository_root, module_name)
