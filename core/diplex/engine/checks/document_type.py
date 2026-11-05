"""Tells a PDF from a DOCX by its bytes, never by its file name or the content type the client sent."""

import io
import lzma
import zipfile
import zlib
from enum import StrEnum
from xml.etree import ElementTree

PDF_SIGNATURE = b"%PDF-"  # required at the very start, so a file can't hide a PDF behind other content
ZIP_SIGNATURE = b"PK\x03\x04"
CONTENT_TYPES_PART = "[Content_Types].xml"  # every Office Open XML package lists its parts' types here
OVERRIDE_TAG = "{http://schemas.openxmlformats.org/package/2006/content-types}Override"
DOCX_MAIN_PART_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
MAX_CONTENT_TYPES_BYTES = 1_000_000  # a real one is a few KB; never unzip more than this to check the type
UNREADABLE_ZIP_ERRORS = (
    zipfile.BadZipFile,  # not a zip, or a damaged one
    KeyError,  # no [Content_Types].xml
    RuntimeError,  # encrypted
    NotImplementedError,  # an unknown compression method
    EOFError,  # cut short
    OSError,  # damaged bzip2 data
    zlib.error,  # damaged deflate data
    lzma.LZMAError,  # damaged LZMA data
)


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
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as package, package.open(CONTENT_TYPES_PART) as content_types_file:
            content_types_xml = content_types_file.read(MAX_CONTENT_TYPES_BYTES + 1)
    except UNREADABLE_ZIP_ERRORS:
        return False
    if len(content_types_xml) > MAX_CONTENT_TYPES_BYTES:
        return False
    try:
        content_types = ElementTree.fromstring(content_types_xml)  # safe with Expat 2.7.2 or later (Python's XML docs)
    except ElementTree.ParseError:
        return False
    # A DOCM (macros), DOTX (template), XLSX or PPTX names a different main part type, so it is not taken for a DOCX.
    return any(override.get("ContentType") == DOCX_MAIN_PART_TYPE for override in content_types.iter(OVERRIDE_TAG))
