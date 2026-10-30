"""Tests for the TypeScript convention rules, run against small repositories written to a temporary folder."""

from __future__ import annotations

from pathlib import Path

from scripts.conventions import check_repository

GOOD_PACKAGE = {
    "app/index.ts": "/** Example app: renders pages. */\n\nexport { renderPages } from './render';\n",
    "app/render/index.ts": (
        "/** Rendering of pages. */\n\n"
        "import { PageSchema } from '../schema';\n\n"
        "/** Render every page and return how many there were. */\n"
        "export function renderPages(count: number): number {\n"
        "  const pageCount = count;\n"
        "  return pageCount;\n"
        "}\n"
    ),
    "app/schema/index.ts": (
        "/** Page schemas. */\n\nimport { z } from 'zod';\n\n"
        "/** A page as the viewer receives it. */\nexport const PageSchema = z.object({ index: z.number() });\n\n"
        "/** The size of one page in points. */\nexport interface PageSize {\n  width: number;\n}\n\n"
        "/** A page index, 1-based. */\nexport type PageIndex = number;\n"
    ),
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


def test_missing_file_docblock_is_reported(tmp_path: Path) -> None:
    """A file that does not open with /** */ breaks the file-docblock rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {"app/index.ts": "export { renderPages } from './render';\n"})
    assert ("app/index.ts", "file-docblock") in rules_found(tmp_path)


def test_function_and_arrow_function_without_comment_are_reported(tmp_path: Path) -> None:
    """Both function declarations and arrow functions need a one-line comment."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "app/render/index.ts": (
            "/** Rendering. */\n\nexport function renderPages(count: number): number {\n  return count;\n}\n\n"
            "export const countPages = (pages: number[]) => pages.length;\n"
        ),
    })
    assert rules_found(tmp_path).count(("app/render/index.ts", "function-comment")) == 2


def test_multi_line_comment_is_reported(tmp_path: Path) -> None:
    """A comment spread over several lines breaks the one-line-comment rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "app/render/index.ts": (
            "/** Rendering. */\n\n/**\n * Render pages.\n */\n"
            "export function renderPages(count: number): number {\n  return count;\n}\n"
        ),
    })
    assert ("app/render/index.ts", "one-line-comment") in rules_found(tmp_path)


def test_schemas_without_comments_are_reported(tmp_path: Path) -> None:
    """A zod schema, an interface and a type alias each need a one-line comment."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "app/schema/index.ts": (
            "/** Page schemas. */\n\nimport { z } from 'zod';\n\n"
            "export const PageSchema = z.object({ index: z.number() });\n\n"
            "export interface PageSize {\n  width: number;\n}\n\nexport type PageIndex = number;\n"
        ),
    })
    assert rules_found(tmp_path).count(("app/schema/index.ts", "schema-comment")) == 3


def test_sibling_import_is_reported(tmp_path: Path) -> None:
    """A non-entry file importing the file next to it breaks the import-boundary rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "app/render/limits.ts": "/** Limits. */\n\n/** Most pages per render. */\nexport const MAX_PAGES = 10;\n",
        "app/render/pages.ts": "/** Page helpers. */\n\nimport { MAX_PAGES } from './limits';\n",
    })
    assert ("app/render/pages.ts", "import-boundary") in rules_found(tmp_path)


def test_reaching_into_another_folders_file_is_reported(tmp_path: Path) -> None:
    """Importing a non-index file of another folder breaks the import-boundary rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "app/schema/page.ts": "/** Page. */\n\n/** Page width. */\nexport const WIDTH = 612;\n",
        "app/render/index.ts": "/** Rendering. */\n\nimport { WIDTH } from '../schema/page';\n",
    })
    assert ("app/render/index.ts", "import-boundary") in rules_found(tmp_path)


def test_package_imports_and_generated_files_are_ignored(tmp_path: Path) -> None:
    """Imports of npm packages are allowed, and generated .gen.ts files are not checked."""
    write_tree(tmp_path, GOOD_PACKAGE | {"app/schema/types.gen.ts": "export type x = number;\n"})
    assert rules_found(tmp_path) == []


def test_folder_without_index_is_reported(tmp_path: Path) -> None:
    """A folder of TypeScript code needs an index.ts."""
    write_tree(tmp_path, GOOD_PACKAGE | {"app/extra/tool.ts": "/** A tool. */\n"})
    assert ("app/extra/index.ts", "folder-entry") in rules_found(tmp_path)


def test_vague_variable_name_is_reported(tmp_path: Path) -> None:
    """A vague variable name like `tmp` breaks the unclear-name rule."""
    write_tree(tmp_path, GOOD_PACKAGE | {
        "app/render/index.ts": (
            "/** Rendering. */\n\n/** Render pages. */\nexport function renderPages(count: number): number {\n"
            "  const tmp = count;\n  return tmp;\n}\n"
        ),
    })
    assert ("app/render/index.ts", "unclear-name") in rules_found(tmp_path)
