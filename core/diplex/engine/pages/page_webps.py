"""Encodes page images as lossless WebP files named page-0001.webp, page-0002.webp, ..."""

import io
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from PIL import Image

from diplex.definition import page_image_filename

# Pillow's defaults. On 69 sample pages they gave a median of 85 KB in 107 ms (PNG: 369 KB);
# method 6 and effort 100 saved 1 KB but took 4 s a page.
WEBP_METHOD = 4  # libwebp's 0 (fastest) to 6 (smallest)
WEBP_EFFORT = 80  # Pillow's `quality`, which for lossless WebP is effort: 0 fastest, 100 smallest


@dataclass(frozen=True)
class PageWebp:
    """A page image encoded as lossless WebP, with its file name."""

    filename: str
    webp_bytes: bytes


def encode_page_webps(page_images: Iterable[Image.Image]) -> Iterator[PageWebp]:
    """Yield each page image as lossless WebP, first page first, then close it; a page is encoded only when asked for."""
    for page_number, page_image in enumerate(page_images, start=1):
        webp_bytes = _encode_lossless_webp(page_image)
        page_image.close()  # frees its pixels before the next page renders, up to 120 MB for a 40 MP page
        yield PageWebp(filename=page_image_filename(page_number), webp_bytes=webp_bytes)


def _encode_lossless_webp(page_image: Image.Image) -> bytes:
    """Encode one image as lossless WebP."""
    webp_buffer = io.BytesIO()
    page_image.save(webp_buffer, format="WEBP", lossless=True, quality=WEBP_EFFORT, method=WEBP_METHOD)
    return webp_buffer.getvalue()
