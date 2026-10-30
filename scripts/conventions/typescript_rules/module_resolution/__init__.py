"""Resolves relative TypeScript import specifiers to the repository files they load."""

from __future__ import annotations

import os
from pathlib import Path

CODE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
INDEX_NAMES = ("index.ts", "index.tsx", "index.js", "index.mjs")


def resolve_specifier(importer: Path, specifier: str) -> Path | None:
    """Return the code file a relative specifier points at, or None for assets and missing files."""
    base = Path(os.path.normpath(importer.parent / specifier))
    if base.suffix in CODE_SUFFIXES:
        if base.is_file():
            return base.resolve()
        # TypeScript lets `./page.js` name `./page.ts`.
        for suffix in (".ts", ".tsx"):
            renamed = base.with_suffix(suffix)
            if renamed.is_file():
                return renamed.resolve()
        return None
    for suffix in CODE_SUFFIXES:
        candidate = Path(f"{base}{suffix}")
        if candidate.is_file():
            return candidate.resolve()
    if base.is_dir():
        for index_name in INDEX_NAMES:
            if (base / index_name).is_file():
                return (base / index_name).resolve()
    return None
