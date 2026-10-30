"""The record of one convention problem: where it is, which rule it breaks, and how to fix it."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    """One broken convention rule at a file and line, with the message that tells how to fix it."""

    path: Path
    line: int
    rule: str
    message: str
