"""Comment rule for TypeScript: every function, class, method and schema has a one-line /** */ above it."""

from __future__ import annotations

import re
from pathlib import Path

from ..report import Violation
from .declarations import Declaration

ONE_LINE_COMMENT = re.compile(r"^/\*\*.*\*/$")


def check_declaration_comments(path: Path, lines: list[str], declarations: list[Declaration]) -> list[Violation]:
    """Return a violation for each declaration without a single-line /** */ comment directly above it."""
    violations: list[Violation] = []
    for declaration in declarations:
        above = _line_above(lines, declaration.line)
        if ONE_LINE_COMMENT.match(above):
            continue
        if above.endswith("*/"):
            message = f"{declaration.kind} `{declaration.name}` comment must be a single line: /** ... */"
            violations.append(Violation(path, declaration.line, "one-line-comment", message))
        else:
            rule = "schema-comment" if declaration.kind == "schema" else "function-comment"
            purpose = "what it is and what it is for" if declaration.kind in ("schema", "class") else "what it does"
            message = f"{declaration.kind} `{declaration.name}` needs a one-line /** */ comment saying {purpose}"
            violations.append(Violation(path, declaration.line, rule, message))
    return violations


def _line_above(lines: list[str], line_number: int) -> str:
    """Return the line directly above a 1-based line, skipping decorators, stripped; empty at a blank line."""
    index = line_number - 2
    while index >= 0:
        stripped = lines[index].strip()
        if not stripped.startswith("@"):
            return stripped
        index -= 1
    return ""
