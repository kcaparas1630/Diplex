"""Tests render_page_images on the real PDFs in samples/. A test is skipped when its PDF is missing (see samples/SOURCES.md)."""

import math
from pathlib import Path

import pytest

from diplex.engine.pages import read_page_sizes, render_page_images

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
US_LETTER_AT_144_DPI = (1224, 1584)  # 8.5 x 11 inches x 144
BUDGET_PAGE_AT_144_DPI = (1260, 1620)  # 8.75 x 11.25 inches x 144
BUDGET_TURNED_PAGE_AT_144_DPI = (1620, 1260)  # the same page with /Rotate 90
A4_PAGE_AT_144_DPI = (1191, 1684)  # 595.32 x 841.92 pt x 2 is 1190.64 x 1683.84, rounded up to cover the whole page
# The US Budget's GPO signature field, /Rect [507 755 602 790] in points from the bottom-left of its 810 pt page,
# as a pixel box (left, top, right, bottom) at 2 pixels per point. It stays blank unless form fields are drawn.
BUDGET_SIGNATURE_FIELD_PIXELS = (1014, 40, 1204, 110)
DRAWN_GREY_LEVEL = 200  # a pixel darker than this, in greyscale, has something drawn on it


def _sample_pdf_parameters() -> list:
    """One test parameter per PDF in samples/, or a single skipped parameter when there are none."""
    sample_paths = sorted(SAMPLES_FOLDER.glob("*.pdf"))
    if not sample_paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no PDF documents in {SAMPLES_FOLDER}"))]
    return [pytest.param(path, id=path.name) for path in sample_paths]


def _sample_bytes(sample_name: str) -> bytes:
    """Read a sample PDF, skipping the test when it isn't in samples/."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")
    return sample_path.read_bytes()


@pytest.mark.parametrize("sample_path", _sample_pdf_parameters())
def test_every_page_renders_at_144_dpi(sample_path):
    """Each real PDF gives one RGB image per page, each 2 pixels per point of the page's size, rounded up."""
    pdf_bytes = sample_path.read_bytes()
    page_sizes = read_page_sizes(pdf_bytes)

    image_count = 0
    for page_size, page_image in zip(page_sizes, render_page_images(pdf_bytes), strict=True):
        image_count += 1
        assert page_image.mode == "RGB"
        assert page_image.size == (math.ceil(page_size.width * 2), math.ceil(page_size.height * 2)), page_size
    assert image_count == len(page_sizes)


def test_a_us_letter_page_is_1224_by_1584_pixels():
    """The IRS form's US Letter pages, 8.5 x 11 inches, come out at 1224 x 1584 px."""
    page_images = render_page_images(_sample_bytes("irs-form-1040-2025.pdf"))

    assert [page_image.size for page_image in page_images] == [US_LETTER_AT_144_DPI] * 2


def test_turned_pages_render_landscape():
    """The US Budget's pages with /Rotate 90 render landscape, the rest portrait."""
    page_images = render_page_images(_sample_bytes("us-budget-fy2025.pdf"))

    assert [page_image.size for page_image in page_images] == (
        [BUDGET_PAGE_AT_144_DPI] * 140 + [BUDGET_TURNED_PAGE_AT_144_DPI] * 40 + [BUDGET_PAGE_AT_144_DPI] * 8
    )


def test_a4_pages_round_up_to_whole_pixels():
    """A4 pages of 595.32 x 841.92 pt, 1190.64 x 1683.84 px at 144 DPI, come out at 1191 x 1684 px."""
    page_images = render_page_images(_sample_bytes("uk-employability-support-guidance-chapter-12.pdf"))

    assert [page_image.size for page_image in page_images] == [A4_PAGE_AT_144_DPI] * 10


def test_form_fields_are_drawn():
    """The US Budget's GPO signature seal, a form field, shows on page 1; without form drawing that area is blank."""
    first_page_image = next(render_page_images(_sample_bytes("us-budget-fy2025.pdf")))

    seal_area = first_page_image.crop(BUDGET_SIGNATURE_FIELD_PIXELS).convert("L")
    drawn_pixel_count = sum(seal_area.histogram()[:DRAWN_GREY_LEVEL])
    assert drawn_pixel_count > seal_area.width * seal_area.height // 100, drawn_pixel_count


@pytest.mark.parametrize("sample_path", _sample_pdf_parameters())
def test_the_first_page_has_something_drawn_on_it(sample_path):
    """Rendering draws the page's content, not just a blank white page."""
    first_page_image = next(render_page_images(sample_path.read_bytes()))

    darkest_value = min(channel_low for channel_low, _ in first_page_image.getextrema())
    assert darkest_value < 128
