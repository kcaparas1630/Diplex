"""Checker output: the Violation record and the report that lists them."""

from .formatting import format_report
from .violation import Violation

__all__ = ["Violation", "format_report"]
