"""Tests for the Python convention rules, run against small repositories written to a temporary folder."""

from __future__ import annotations

from pathlib import Path

from scripts.conventions import check_repository

GOOD_PACKAGE = {
    "pkg/__init__.py": '"""Example package."""\n\nfrom .core import run\n',
    "pkg/core/__init__.py": '"""Core logic."""\n\nfrom .runner import run\n',
    "pkg/core/runner.py": (
        '"""Runs the example."""\n\n'
        "from ..report import Report\n\n\n"
        "def run(count: int) -> Report:\n"
        '    """Run the example and return its report."""\n'
        "    for i in range(count):\n"
        "        pass\n"
        "    return Report()\n"
    ),
    "pkg/report/__init__.py": '"""Report types."""\n\n\nclass Report:\n    """The result of one run."""\n',
}


def write_tree(root: Path, files: dict[str, str]) -> None:
    """Write each relative path and its text under the root, creating folders as needed."""
    for relative_path, text in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def rules_found(root: Path) -> list[tuple[str, str]]:
    """Return (relative path, rule) for every violation in the repository at root."""
    resolved = root.resolve()
    return [(found.path.relative_to(resolved).as_posix(), found.rule) for found in check_repository(root)]


def test_a_package_that_follows_every_rule_passes(tmp_path: Path) -> None:
    """A well-formed package produces no violations."""
    write_tree(tmp_path, GOOD_PACKAGE)
    assert rules_found(tmp_path) == []


def test_function_without_docstring_is_reported(tmp_path: Path) -> None:
    """A function with no docstring breaks the function-comment rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/core/runner.py": '"""Runs the example."""\n\n\ndef run(count: int) -> int:\n    return count\n',
    })
    assert ("pkg/core/runner.py", "function-comment") in rules_found(tmp_path)


def test_multi_line_docstring_is_reported(tmp_path: Path) -> None:
    """A function docstring longer than one line breaks the one-line-comment rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/core/runner.py": (
            '"""Runs the example."""\n\n\ndef run(count: int) -> int:\n'
            '    """Run the example.\n\n    More detail.\n    """\n    return count\n'
        ),
    })
    assert ("pkg/core/runner.py", "one-line-comment") in rules_found(tmp_path)


def test_schema_class_without_docstring_is_reported(tmp_path: Path) -> None:
    """A class (a Pydantic model or dataclass) without a docstring breaks the schema-comment rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/report/__init__.py": '"""Report types."""\n\n\nclass Report:\n    pages: int = 0\n',
    })
    assert ("pkg/report/__init__.py", "schema-comment") in rules_found(tmp_path)


def test_missing_module_docstring_is_reported(tmp_path: Path) -> None:
    """A file without a module docstring breaks the file-docblock rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {"pkg/report/__init__.py": "class Report:\n    \"\"\"The result.\"\"\"\n"})
    assert ("pkg/report/__init__.py", "file-docblock") in rules_found(tmp_path)


def test_sibling_import_is_reported(tmp_path: Path) -> None:
    """A non-entry file importing a file next to it breaks the import-boundary rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/core/limits.py": '"""Limits."""\n\nMAX_PAGES = 10\n',
        "pkg/core/runner.py": '"""Runs the example."""\n\nfrom .limits import MAX_PAGES\n',
    })
    assert ("pkg/core/runner.py", "import-boundary") in rules_found(tmp_path)


def test_reaching_into_another_folders_file_is_reported(tmp_path: Path) -> None:
    """Importing a non-entry file of another folder breaks the import-boundary rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/report/format.py": '"""Formats reports."""\n\nWIDTH = 80\n',
        "pkg/core/runner.py": '"""Runs the example."""\n\nfrom ..report.format import WIDTH\n',
    })
    assert ("pkg/core/runner.py", "import-boundary") in rules_found(tmp_path)


def test_absolute_import_into_another_folders_file_is_reported(tmp_path: Path) -> None:
    """The boundary rule also applies to absolute imports."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/report/format.py": '"""Formats reports."""\n\nWIDTH = 80\n',
        "pkg/core/runner.py": '"""Runs the example."""\n\nimport pkg.report.format\n',
    })
    assert ("pkg/core/runner.py", "import-boundary") in rules_found(tmp_path)


def test_importing_a_parent_folder_is_reported(tmp_path: Path) -> None:
    """A file importing its parent package breaks the import-boundary rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/core/runner.py": '"""Runs the example."""\n\nfrom .. import core\n',
    })
    assert ("pkg/core/runner.py", "import-boundary") in rules_found(tmp_path)


def test_sub_folder_and_entry_imports_are_allowed(tmp_path: Path) -> None:
    """Entries may compose their own files, and any file may import its sub-folders."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/core/runner.py": '"""Runs the example."""\n\nfrom .steps import STEPS\n',
        "pkg/core/steps/__init__.py": '"""Steps."""\n\nSTEPS = []\n',
    })
    assert rules_found(tmp_path) == []


def test_vague_and_short_names_are_reported(tmp_path: Path) -> None:
    """Vague names like `data` and cryptic short ones like `pg` break the unclear-name rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/core/runner.py": (
            '"""Runs the example."""\n\n\ndef run(pg: int) -> int:\n'
            '    """Run the example."""\n    data = pg\n    return data\n'
        ),
    })
    assert rules_found(tmp_path).count(("pkg/core/runner.py", "unclear-name")) == 2


def test_folder_without_entry_is_reported_but_tests_are_exempt(tmp_path: Path) -> None:
    """A folder of code needs an __init__.py; a tests folder does not."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/extra/tool.py": '"""A tool."""\n',
        "pkg/tests/test_tool.py": '"""Tool tests."""\n\nfrom pkg.extra.tool import __doc__ as text\n',
    })
    assert rules_found(tmp_path) == [("pkg/extra/__init__.py", "folder-entry")]


def test_long_file_and_vague_file_name_are_reported(tmp_path: Path) -> None:
    """A file over the line limit and a file named utils.py are both reported."""
    long_body = "".join(f"VALUE_{number} = {number}\n" for number in range(310))
    write_tree(tmp_path, GOOD_PACKAGE | {
        "pkg/core/tables.py": '"""Tables."""\n' + long_body,
        "pkg/core/utils.py": '"""Odds and ends."""\n',
    })
    found = rules_found(tmp_path)
    assert ("pkg/core/tables.py", "file-length") in found
    assert ("pkg/core/utils.py", "unclear-file-name") in found
