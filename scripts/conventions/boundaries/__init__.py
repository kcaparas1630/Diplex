"""Folder boundaries shared by every language: the rule for what a file may import."""

from .import_rule import import_problem, is_entry_file

__all__ = ["import_problem", "is_entry_file"]
