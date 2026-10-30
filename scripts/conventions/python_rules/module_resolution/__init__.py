"""Resolves Python import statements to the repository files they load, so the import rule can judge them."""

from __future__ import annotations

from pathlib import Path

from ...settings import PYTHON_SOURCE_ROOTS


def resolve_absolute(repository_root: Path, dotted_name: str) -> Path | None:
    """Return the repository file an absolute import names, or None for a third-party or standard module."""
    parts = dotted_name.split(".")
    for source_root in PYTHON_SOURCE_ROOTS:
        module_file = _module_file(repository_root.joinpath(source_root, *parts))
        if module_file:
            return module_file
    return None


def resolve_relative(importer: Path, level: int, dotted_name: str) -> Path | None:
    """Return the repository file a relative import names (`from ..x import y`), or None if it does not exist."""
    package_folder = importer.parent
    for _ in range(level - 1):
        package_folder = package_folder.parent
    parts = [part for part in dotted_name.split(".") if part]
    return _module_file(package_folder.joinpath(*parts))


def _module_file(module_path: Path) -> Path | None:
    """Return `module_path.py`, or `module_path/__init__.py` for a package, whichever exists."""
    plain_module = Path(f"{module_path}.py")
    if plain_module.is_file() and plain_module.resolve().stem == module_path.name:
        return plain_module.resolve()
    package_entry = module_path / "__init__.py"
    if package_entry.is_file() and package_entry.resolve().parent.name == module_path.name:
        return package_entry.resolve()
    return None
