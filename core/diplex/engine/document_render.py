"""Renders a PDF, or a DOCX converted to PDF, into its page sizes and lossless WebP page images."""

import threading
from collections.abc import Callable
from dataclasses import dataclass

from diplex.definition import PageSize
from diplex.engine.checks import check_docx_zip_limits, reject_macro_enabled_docx
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


def render_docx(docx_bytes: bytes, convert_docx_to_pdf: Callable[[bytes], bytes]) -> RenderedDocument:
    """Check the DOCX, convert it to PDF with the given converter, then render that PDF, so images and PDF match page for page."""
    check_docx_zip_limits(docx_bytes)  # before anything else unzips it
    reject_macro_enabled_docx(docx_bytes)  # before LibreOffice ever opens it
    converted_pdf = convert_docx_to_pdf(docx_bytes)  # outside the PDFium lock: LibreOffice is a separate process
    rendered_pdf = render_pdf(converted_pdf)
    return RenderedDocument(
        page_sizes=rendered_pdf.page_sizes, page_webps=rendered_pdf.page_webps, converted_pdf=converted_pdf
    )
