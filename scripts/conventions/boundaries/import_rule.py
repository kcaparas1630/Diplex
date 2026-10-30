"""The import rule from convention 008: which repository files one source file may import.

A file may import anything inside its own sub-folders, and another folder only through that
folder's public entry (`__init__.py`, `index.ts`). It never imports a sibling file or a parent
folder. Only an entry file may import the files of its own folder, to compose them.
"""

from __future__ import annotations

from pathlib import Path

from ..settings import ENTRY_FILE_NAMES


def is_entry_file(path: Path) -> bool:
    """Tell whether a file is its folder's public entry."""
    return path.name in ENTRY_FILE_NAMES


def import_problem(importer: Path, target: Path) -> str | None:
    """Explain why `importer` may not import `target`, or return None when the import is allowed."""
    importer_folder = importer.parent
    target_folder = target.parent
    if target_folder != importer_folder and importer_folder in target_folder.parents:
        return None
    if target_folder == importer_folder:
        if is_entry_file(importer):
            return None
        return (
            "imports a sibling file; move the shared code into a sub-folder, "
            "or let this folder's entry file compose the two"
        )
    if target_folder in importer_folder.parents:
        return "imports from a parent folder; parents import their sub-folders, never the other way round"
    if is_entry_file(target):
        return None
    return "reaches into another folder's file; import that folder's public entry (__init__.py / index.ts) instead"
