"""Renders each page of a PDF to an image at 144 DPI, one page at a time."""

import math
from collections.abc import Iterator

import pypdfium2
from PIL import Image

from diplex.engine.pdf_loading import UnreadablePdfError, load_pdf_document

RENDER_SCALE = 2  # 144 DPI: PDF sizes are in points, 72 to the inch
MAX_PAGE_PIXELS = 40_000_000  # above an A0 drawing (32 MP at 144 DPI); a 200-inch page would need 2.5 GB
MAX_PAGE_SIDE_PIXELS = 16_383  # WebP's limit per side, 113.7 inches at 144 DPI; a long receipt can pass the pixel limit


class PageTooLargeError(Exception):
    """A page's image at 144 DPI would be over MAX_PAGE_PIXELS pixels, or over MAX_PAGE_SIDE_PIXELS on a side."""


def render_page_images(pdf_bytes: bytes) -> Iterator[Image.Image]:
    """Yield each page as an RGB image at 144 DPI, first page first, rendering a page only when it is asked for."""
    with load_pdf_document(pdf_bytes) as pdf_document:
        try:
            pdf_document.init_forms()  # draws form fields, like the GPO seal on the US Budget; must come before pages
            _refuse_pages_too_large(pdf_document)
            for page_offset in range(len(pdf_document)):
                yield _render_page(pdf_document, page_offset)
        except pypdfium2.PdfiumError as error:
            raise UnreadablePdfError(f"PDFium could not render the PDF: {error}") from error


def _refuse_pages_too_large(pdf_document: pypdfium2.PdfDocument) -> None:
    """Raise PageTooLargeError before any rendering if a page's image would be over either limit."""
    for page_offset in range(len(pdf_document)):
        width_points, height_points = pdf_document.get_page_size(page_offset)
        # pypdfium2 rounds the bitmap up to whole pixels, so it covers the whole page.
        width_pixels, height_pixels = math.ceil(width_points * RENDER_SCALE), math.ceil(height_points * RENDER_SCALE)
        page_pixels = f"page {page_offset + 1} would render at {width_pixels} x {height_pixels} pixels"
        if width_pixels * height_pixels > MAX_PAGE_PIXELS:
            raise PageTooLargeError(f"{page_pixels}, over the limit of {MAX_PAGE_PIXELS:,}")
        if max(width_pixels, height_pixels) > MAX_PAGE_SIDE_PIXELS:
            raise PageTooLargeError(f"{page_pixels}, over WebP's limit of {MAX_PAGE_SIDE_PIXELS:,} on a side")


def _render_page(pdf_document: pypdfium2.PdfDocument, page_offset: int) -> Image.Image:
    """Render one page at 144 DPI, then free PDFium's page and bitmap."""
    page = pdf_document[page_offset]
    try:
        bitmap = page.render(scale=RENDER_SCALE)  # turns the page by its /Rotate, as its size does
        try:
            return bitmap.to_pil()  # copies PDFium's BGR pixels into a new RGB image, so the bitmap can be freed
        finally:
            bitmap.close()
    finally:
        page.close()
