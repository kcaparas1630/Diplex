"""Renders a PDF into its page sizes and lossless WebP page images, one document in PDFium at a time."""

import threading
from dataclasses import dataclass

from diplex.definition import PageSize
from diplex.engine.pages import PageWebp, encode_page_webps, read_page_sizes, render_page_images

# PDFium must never take calls from two threads at once, even for different documents (pypdfium2's docs), and FastAPI
# runs routes in a thread pool. The lock covers the whole document, since render_page_images keeps it open between pages.
PDFIUM_LOCK = threading.Lock()


@dataclass(frozen=True)
class RenderedDocument:
    """A rendered document: each page's size, and each page as a lossless WebP, first page first."""

    page_sizes: list[PageSize]
    page_webps: list[PageWebp]


def render_pdf(pdf_bytes: bytes) -> RenderedDocument:
    """Read each page's size and encode each page as a lossless WebP, waiting for any other document in PDFium."""
    with PDFIUM_LOCK:
        page_sizes = read_page_sizes(pdf_bytes)
        page_webps = list(encode_page_webps(render_page_images(pdf_bytes)))
    return RenderedDocument(page_sizes=page_sizes, page_webps=page_webps)
