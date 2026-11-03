"""Part names, media types and file names of a /render response."""

from enum import StrEnum


class RenderPart(StrEnum):
    """Part names in a /render response."""

    MANIFEST = "manifest"  # no file name, so formData().get() returns a string
    PAGE_IMAGE = "page"  # one part per page, same name, in page order
    CONVERTED_PDF = "pdf"  # DOCX uploads only


RENDER_PART_MEDIA_TYPES = {
    RenderPart.MANIFEST: "application/json",
    RenderPart.PAGE_IMAGE: "image/webp",
    RenderPart.CONVERTED_PDF: "application/pdf",
}

CONVERTED_PDF_FILENAME = "document.pdf"
PAGE_NUMBER_DIGITS = 4  # names sort in page order up to page 9999


def page_image_filename(page_index: int) -> str:
    """Return a page image's file name, e.g. page-0001.webp."""
    if page_index < 1:
        raise ValueError(f"page numbers start at 1, not {page_index}")
    return f"page-{page_index:0{PAGE_NUMBER_DIGITS}d}.webp"
