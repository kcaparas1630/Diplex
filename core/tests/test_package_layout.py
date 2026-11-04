"""Checks that every folder in the diplex package imports and has a docstring."""

import importlib

import pytest

PACKAGE_FOLDERS = [
    "diplex",
    "diplex.definition",
    "diplex.engine",
    "diplex.engine.checks",
    "diplex.engine.docx_to_pdf",
    "diplex.engine.pages",
    "diplex.engine.pdf_loading",
    "diplex.api",
]


@pytest.mark.parametrize("module_name", PACKAGE_FOLDERS)
def test_each_package_folder_imports_and_describes_itself(module_name):
    """Every folder of the package imports cleanly and its entry has a docstring."""
    package_entry = importlib.import_module(module_name)

    assert (package_entry.__doc__ or "").strip()
