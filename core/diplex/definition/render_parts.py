"""The names, media types and file names of the parts in a /render response (ADR 010), defined in one place.

Consumers read the response with formData(). The manifest part has no file name, so it arrives as a string of
JSON; each page image and the converted PDF arrive as files. All page images share one part name, in page
order, the way RFC 7578 section 4.3 sends several files for one field, so formData().getAll() returns them
in order.
"""

from enum import StrEnum


class RenderPart(StrEnum):
    """The name of each part of a /render response, as consumers pass it to formData().get()."""

    MANIFEST = "manifest"
    PAGE_IMAGE = "page"
    CONVERTED_PDF = "pdf"


RENDER_PART_MEDIA_TYPES = {
    RenderPart.MANIFEST: "application/json",
    RenderPart.PAGE_IMAGE: "image/webp",
    RenderPart.CONVERTED_PDF: "application/pdf",
}

CONVERTED_PDF_FILENAME = "document.pdf"
PAGE_NUMBER_DIGITS = 4  # page-0001.webp: names sort in page order up to page 9999


def page_image_filename(page_index: int) -> str:
    """Name a page image after its page number, zero-padded: page 1 is page-0001.webp."""
    if page_index < 1:
        raise ValueError(f"page numbers start at 1, not {page_index}")
    return f"page-{page_index:0{PAGE_NUMBER_DIGITS}d}.webp"
