"""Turns violations into the report printed for people and fed back to Claude Code."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .violation import Violation


def format_report(repository_root: Path, violations: list[Violation]) -> str:
    """Group violations by file and render them as a readable, fixable report."""
    by_file: dict[Path, list[Violation]] = defaultdict(list)
    for violation in violations:
        by_file[violation.path].append(violation)
    lines = [
        f"Convention check failed: {len(violations)} problem(s) in {len(by_file)} file(s).",
        "Rules: docs/code-convention/007 to 010. Fix each problem, then run `python -m scripts.conventions` again.",
        "",
    ]
    for path in sorted(by_file):
        lines.append(_display_path(repository_root, path))
        for violation in sorted(by_file[path], key=lambda found: found.line):
            lines.append(f"  line {violation.line}  [{violation.rule}] {violation.message}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _display_path(repository_root: Path, path: Path) -> str:
    """Show a path relative to the repository when it is inside it."""
    try:
        return path.relative_to(repository_root).as_posix()
    except ValueError:
        return path.as_posix()
