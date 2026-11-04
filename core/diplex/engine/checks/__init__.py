"""Checks on an upload before anything renders it: whether it is a PDF or a DOCX."""

from .document_type import DocumentType, UnsupportedDocumentError, detect_document_type

__all__ = ["DocumentType", "UnsupportedDocumentError", "detect_document_type"]
