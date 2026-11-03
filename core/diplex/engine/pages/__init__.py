"""Reads a PDF's pages: each page's size in points."""

from .page_sizes import UnreadablePdfError, read_page_sizes

__all__ = ["UnreadablePdfError", "read_page_sizes"]
