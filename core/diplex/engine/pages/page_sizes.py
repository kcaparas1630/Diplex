"""Reads each page's size in points from a PDF."""

import pypdfium2
from pydantic import ValidationError

from diplex.definition import PageSize
from diplex.engine.pdf_loading import UnreadablePdfError, load_pdf_document

SIZE_DECIMALS = 2  # PDFium returns float32 sizes, e.g. A4 as 595.303955078125; 0.01 pt is far below a pixel


def read_page_sizes(pdf_bytes: bytes) -> list[PageSize]:
    """Return each page's number, width and height in points, first page first."""
    with load_pdf_document(pdf_bytes) as pdf_document:
        try:
            # Size as shown, so it matches the rendered image: /Rotate 90 or 270 swaps width and height.
            pdfium_sizes = [pdf_document.get_page_size(page_offset) for page_offset in range(len(pdf_document))]
        except pypdfium2.PdfiumError as error:
            raise UnreadablePdfError(f"PDFium could not read the PDF: {error}") from error
    try:
        return [
            PageSize(index=page_number, width=round(width, SIZE_DECIMALS), height=round(height, SIZE_DECIMALS))
            for page_number, (width, height) in enumerate(pdfium_sizes, start=1)
        ]
    except ValidationError as error:
        raise UnreadablePdfError("the PDF has a page smaller than 0.01 points") from error
