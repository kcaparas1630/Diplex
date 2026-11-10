"""Reads a PDF's pages: each page's size in points, and each page as an image at 144 DPI, encoded as WebP
(lossless for text pages, lossy for scanned or photo-heavy ones; page_content/ tells them apart)."""

from diplex.engine.pdf_loading import UnreadablePdfError

from .page_images import PageTooLargeError, render_page_images
from .page_sizes import read_page_sizes
from .page_webps import PageWebp, encode_page_webps

__all__ = [
    "PageTooLargeError",
    "PageWebp",
    "UnreadablePdfError",
    "encode_page_webps",
    "read_page_sizes",
    "render_page_images",
]
