"""The rendering steps: checks/ tells a PDF from a DOCX, docx_to_pdf/ converts a DOCX with unoserver, pdf_loading/ loads a PDF, and pages/ reads and renders its pages."""

from .checks import DocumentType, UnsupportedDocumentError, detect_document_type
from .docx_to_pdf import UnoserverUnavailableError
from .document_render import RenderedDocument, render_docx, render_pdf
from .pages import PageTooLargeError, UnreadablePdfError

__all__ = [
    "DocumentType",
    "PageTooLargeError",
    "RenderedDocument",
    "UnreadablePdfError",
    "UnoserverUnavailableError",
    "UnsupportedDocumentError",
    "detect_document_type",
    "render_docx",
    "render_pdf",
]
