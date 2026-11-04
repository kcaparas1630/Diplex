"""Loads a PDF into PDFium."""

import pypdfium2


class UnreadablePdfError(Exception):
    """PDFium couldn't load or read the PDF."""


def load_pdf_document(pdf_bytes: bytes) -> pypdfium2.PdfDocument:
    """Load a PDF from its bytes, raising UnreadablePdfError if PDFium can't."""
    try:
        return pypdfium2.PdfDocument(pdf_bytes)
    except pypdfium2.PdfiumError as error:
        raise UnreadablePdfError(f"PDFium could not read the PDF: {error}") from error
