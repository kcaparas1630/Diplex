"""Tells a PDF from a DOCX by its bytes, never by its file name or the content type the client sent."""

from enum import StrEnum

from .docx_package import read_part_content_types

PDF_SIGNATURE = b"%PDF-"  # required at the very start, so a file can't hide a PDF behind other content
ZIP_SIGNATURE = b"PK\x03\x04"
DOCX_MAIN_PART_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


class DocumentType(StrEnum):
    """The kinds of document the engine renders."""

    DOCX = "docx"
    PDF = "pdf"


class UnsupportedDocumentError(Exception):
    """The upload is neither a PDF nor a DOCX."""


def detect_document_type(document_bytes: bytes) -> DocumentType:
    """Return whether the bytes are a PDF or a DOCX, raising UnsupportedDocumentError for anything else."""
    if document_bytes.startswith(PDF_SIGNATURE):
        return DocumentType.PDF
    if document_bytes.startswith(ZIP_SIGNATURE) and _is_word_document_package(document_bytes):
        return DocumentType.DOCX
    raise UnsupportedDocumentError("the upload is not a PDF or a DOCX")


def _is_word_document_package(zip_bytes: bytes) -> bool:
    """Tell whether a zip's [Content_Types].xml names a Word document part, as a DOCX's does."""
    part_content_types = read_part_content_types(zip_bytes)
    # A DOCM (macros), DOTX (template), XLSX or PPTX names a different main part type, so it is not taken for a DOCX.
    return part_content_types is not None and DOCX_MAIN_PART_TYPE in part_content_types
