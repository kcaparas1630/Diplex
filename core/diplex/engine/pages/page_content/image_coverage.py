"""Measures how much of a page its images cover, which tells a scanned or photo-heavy page from a text page (ADR 001 §4)."""

import pypdfium2
from PIL import Image

IMAGE_COVERAGE_KEY = "diplex_image_coverage"  # set on each rendered page image, read by the WebP encoder
PHOTO_HEAVY_COVERAGE = 0.5  # at least half the page under images: a scan, a photo page or a full-page picture
MAX_FORM_DEPTH = 15  # images inside nested form XObjects count too (pypdfium2's default depth)


def measure_image_coverage(page: pypdfium2.PdfPage) -> float:
    """The share of the page's box covered by image objects, from 0 to 1; overlapping images count once each, capped at 1."""
    left, bottom, right, top = page.get_bbox()
    page_area = (right - left) * (top - bottom)
    if page_area <= 0:
        return 0.0
    covered_area = 0.0
    for image_object in page.get_objects(filter=[pypdfium2.raw.FPDF_PAGEOBJ_IMAGE], max_depth=MAX_FORM_DEPTH):
        image_left, image_bottom, image_right, image_top = image_object.get_bounds()
        covered_width = max(0.0, min(image_right, right) - max(image_left, left))
        covered_height = max(0.0, min(image_top, top) - max(image_bottom, bottom))
        covered_area += covered_width * covered_height
    return min(covered_area / page_area, 1.0)


def suits_lossy_encoding(page_image: Image.Image) -> bool:
    """Tell whether a rendered page is scanned or photo-heavy, so lossy WebP keeps it small at no visible cost."""
    return page_image.info.get(IMAGE_COVERAGE_KEY, 0.0) >= PHOTO_HEAVY_COVERAGE
