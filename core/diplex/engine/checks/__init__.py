"""Checks on an upload before anything renders it: PDF or DOCX, and for a DOCX its zip limits and whether it carries macros."""

from .docx_macros import MacroEnabledDocumentError, reject_macro_enabled_docx
from .docx_zip_limits import DamagedDocxError, DocxLimitsExceededError, check_docx_zip_limits
from .document_type import DocumentType, UnsupportedDocumentError, detect_document_type

__all__ = [
    "DamagedDocxError",
    "DocumentType",
    "DocxLimitsExceededError",
    "MacroEnabledDocumentError",
    "UnsupportedDocumentError",
    "check_docx_zip_limits",
    "detect_document_type",
    "reject_macro_enabled_docx",
]
