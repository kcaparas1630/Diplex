"""Finds the declarations in TypeScript source that the comment and naming rules look at.

Line patterns, not a parser: they cover the usual one-line forms of functions, arrow functions,
classes, methods, interfaces, type aliases, enums and zod schemas. ESLint replaces this once the
TypeScript packages are scaffolded (convention 010).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

IDENTIFIER = r"([A-Za-z_$][\w$]*)"
EXPORT_PREFIX = r"^\s*(?:export\s+)?(?:default\s+)?(?:declare\s+)?"

DECLARATION_PATTERNS = (
    ("schema", re.compile(EXPORT_PREFIX + r"(?:const|let)\s+" + IDENTIFIER + r"\s*(?::[^=]+)?=\s*z\.")),
    ("function", re.compile(EXPORT_PREFIX + r"(?:async\s+)?function\*?\s+" + IDENTIFIER)),
    ("function", re.compile(
        EXPORT_PREFIX + r"(?:const|let)\s+" + IDENTIFIER
        + r"\s*(?::[^=]+)?=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)"
    )),
    ("class", re.compile(EXPORT_PREFIX + r"(?:abstract\s+)?class\s+" + IDENTIFIER)),
    ("schema", re.compile(EXPORT_PREFIX + r"interface\s+" + IDENTIFIER)),
    ("schema", re.compile(EXPORT_PREFIX + r"type\s+" + IDENTIFIER + r"\s*(?:<[^=]*>)?\s*=")),
    ("schema", re.compile(EXPORT_PREFIX + r"(?:const\s+)?enum\s+" + IDENTIFIER)),
    ("method", re.compile(
        r"^\s+(?:(?:public|private|protected|static|readonly|async|override|get|set)\s+)*"
        + IDENTIFIER + r"\s*(?:<[^>]*>)?\([^)]*\)\s*(?::\s*[^{=]+)?\{\s*$"
    )),
)

VARIABLE_PATTERN = re.compile(r"\b(?:const|let|var)\s+" + IDENTIFIER + r"\s*[:=]")

NOT_METHOD_NAMES = frozenset({"if", "for", "while", "switch", "catch", "function", "return", "with"})


@dataclass(frozen=True)
class Declaration:
    """A function, class, method or schema declared on one line of a TypeScript file."""

    line: int
    kind: str
    name: str


def find_declarations(lines: list[str]) -> list[Declaration]:
    """Return every declaration that needs a one-line comment, in file order."""
    declarations: list[Declaration] = []
    for line_number, line in enumerate(lines, start=1):
        for kind, pattern in DECLARATION_PATTERNS:
            found = pattern.match(line)
            if found and not (kind == "method" and found.group(1) in NOT_METHOD_NAMES):
                declarations.append(Declaration(line_number, kind, found.group(1)))
                break
    return declarations


def find_variable_names(lines: list[str]) -> list[tuple[int, str]]:
    """Return the line and name of every `const`, `let` and `var` the file declares."""
    names: list[tuple[int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        for found in VARIABLE_PATTERN.finditer(line):
            names.append((line_number, found.group(1)))
    return names
