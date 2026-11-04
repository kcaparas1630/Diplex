"""Loads a PDF's bytes into memory, for reading page sizes and rendering pages."""

from .load_pdf import UnreadablePdfError, load_pdf_document

__all__ = ["UnreadablePdfError", "load_pdf_document"]
