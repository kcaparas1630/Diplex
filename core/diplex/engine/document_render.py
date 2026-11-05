"""Renders a PDF, or a DOCX converted to PDF, into its page sizes and lossless WebP page images."""

import threading
from dataclasses import dataclass

from diplex.definition import PageSize
from diplex.engine.docx_to_pdf import convert_docx_to_pdf
from diplex.engine.pages import PageWebp, encode_page_webps, read_page_sizes, render_page_images

# PDFium must never take calls from two threads at once, even for different documents (pypdfium2's docs), and FastAPI
# runs routes in a thread pool. The lock covers the whole document, since render_page_images keeps it open between pages.
PDFIUM_LOCK = threading.Lock()


@dataclass(frozen=True)
class RenderedDocument:
    """A rendered document: each page's size and lossless WebP, first page first, and the PDF a DOCX became."""

    page_sizes: list[PageSize]
    page_webps: list[PageWebp]
    converted_pdf: bytes | None = None  # None for a PDF upload, which gets no PDF back


def render_pdf(pdf_bytes: bytes) -> RenderedDocument:
    """Read each page's size and encode each page as a lossless WebP, waiting for any other document in PDFium."""
    with PDFIUM_LOCK:
        page_sizes = read_page_sizes(pdf_bytes)
        page_webps = list(encode_page_webps(render_page_images(pdf_bytes)))
    return RenderedDocument(page_sizes=page_sizes, page_webps=page_webps)


def render_docx(docx_bytes: bytes) -> RenderedDocument:
    """Convert a DOCX to PDF with unoserver, then render that PDF, so the images and the PDF match page for page."""
    converted_pdf = convert_docx_to_pdf(docx_bytes)  # outside the PDFium lock: LibreOffice is a separate process
    rendered_pdf = render_pdf(converted_pdf)
    return RenderedDocument(
        page_sizes=rendered_pdf.page_sizes, page_webps=rendered_pdf.page_webps, converted_pdf=converted_pdf
    )
