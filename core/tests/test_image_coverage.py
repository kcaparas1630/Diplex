"""Tests measuring a page's image coverage, with stand-in PDFium pages and objects; no PDFs are generated."""

import pypdfium2
import pytest

from diplex.engine.pages.page_content import measure_image_coverage

US_LETTER_BOX = (0.0, 0.0, 612.0, 792.0)


class StandInImage:
    """A page object with bounds, like pypdfium2's image objects."""

    def __init__(self, bounds: tuple[float, float, float, float]) -> None:
        """Hold the bounds as (left, bottom, right, top)."""
        self._bounds = bounds

    def get_bounds(self) -> tuple[float, float, float, float]:
        """Return the bounds."""
        return self._bounds


class StandInPage:
    """A page with a box and image objects, like pypdfium2's PdfPage."""

    def __init__(self, page_box: tuple[float, float, float, float], image_bounds: list[tuple[float, float, float, float]]) -> None:
        """Hold the page box and the bounds of each image on it."""
        self._page_box = page_box
        self._image_bounds = image_bounds

    def get_bbox(self) -> tuple[float, float, float, float]:
        """Return the page box."""
        return self._page_box

    def get_objects(self, filter: list[int], max_depth: int) -> list[StandInImage]:
        """Return the image objects, checking that only images are asked for, nested forms included."""
        assert filter == [pypdfium2.raw.FPDF_PAGEOBJ_IMAGE] and max_depth > 0
        return [StandInImage(bounds) for bounds in self._image_bounds]


@pytest.mark.parametrize(
    ("image_bounds", "expected_coverage"),
    [
        ([], 0.0),
        ([(0.0, 0.0, 612.0, 792.0)], 1.0),
        ([(0.0, 0.0, 306.0, 792.0)], 0.5),
        ([(-100.0, -100.0, 306.0, 892.0)], 0.5),
        ([(0.0, 0.0, 612.0, 792.0), (0.0, 0.0, 612.0, 792.0)], 1.0),
        ([(50.0, 700.0, 150.0, 760.0)], 6000 / (612 * 792)),
    ],
    ids=["text-only", "full-page-scan", "half-page-photo", "photo-bleeding-off-the-page", "stacked-images-capped", "small-logo"],
)
def test_coverage_is_the_share_of_the_page_under_images(image_bounds, expected_coverage):
    """Coverage is the image area inside the page box over the page area, clipped to the page and capped at 1."""
    assert measure_image_coverage(StandInPage(US_LETTER_BOX, image_bounds)) == pytest.approx(expected_coverage)


def test_a_page_with_no_area_has_no_coverage():
    """A degenerate page box gives 0 rather than dividing by zero."""
    assert measure_image_coverage(StandInPage((0.0, 0.0, 0.0, 792.0), [(0.0, 0.0, 10.0, 10.0)])) == 0.0
