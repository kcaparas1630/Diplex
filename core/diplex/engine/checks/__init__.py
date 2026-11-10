"""Checks on an upload before anything renders it: whether it is a PDF or a DOCX, and whether a DOCX carries macros."""

from .docx_macros import MacroEnabledDocumentError, reject_macro_enabled_docx
from .document_type import DocumentType, UnsupportedDocumentError, detect_document_type

__all__ = [
    "DocumentType",
    "MacroEnabledDocumentError",
    "UnsupportedDocumentError",
    "detect_document_type",
    "reject_macro_enabled_docx",
]
