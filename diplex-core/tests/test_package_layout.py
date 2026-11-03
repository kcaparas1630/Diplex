"""Checks that every folder in diplex_core imports and has a docstring."""

import importlib

import pytest

PACKAGE_FOLDERS = [
    "diplex_core",
    "diplex_core.engine",
    "diplex_core.engine.docx_to_pdf",
]


@pytest.mark.parametrize("module_name", PACKAGE_FOLDERS)
def test_each_package_folder_imports_and_describes_itself(module_name):
    """Every folder of the package imports cleanly and its entry has a docstring."""
    package_entry = importlib.import_module(module_name)

    assert (package_entry.__doc__ or "").strip()
