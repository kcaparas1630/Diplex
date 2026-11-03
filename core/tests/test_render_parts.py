"""Unit tests for the /render response's part names, media types and file names."""

import pytest

from diplex.definition import CONVERTED_PDF_FILENAME, RENDER_PART_MEDIA_TYPES, RenderPart, page_image_filename


def test_part_names_are_the_ones_consumers_read():
    """Consumers call formData().get("manifest"), getAll("page") and get("pdf")."""
    assert [part.value for part in RenderPart] == ["manifest", "page", "pdf"]


def test_every_part_has_its_media_type():
    """The manifest is JSON, page images are WebP, and the converted PDF is a PDF."""
    assert RENDER_PART_MEDIA_TYPES == {
        RenderPart.MANIFEST: "application/json",
        RenderPart.PAGE_IMAGE: "image/webp",
        RenderPart.CONVERTED_PDF: "application/pdf",
    }


def test_the_converted_pdf_has_a_fixed_file_name():
    """The converted PDF part is always named document.pdf."""
    assert CONVERTED_PDF_FILENAME == "document.pdf"


@pytest.mark.parametrize(
    ("page_index", "expected_filename"),
    [(1, "page-0001.webp"), (42, "page-0042.webp"), (9999, "page-9999.webp"), (12345, "page-12345.webp")],
)
def test_page_images_are_named_by_zero_padded_page_number(page_index, expected_filename):
    """Page numbers are padded to four digits and keep growing past 9999."""
    assert page_image_filename(page_index) == expected_filename


def test_page_image_names_sort_in_page_order():
    """Sorting the names as text gives page order, so a bucket listing reads in order."""
    filenames = [page_image_filename(page_index) for page_index in range(1, 1001)]

    assert sorted(filenames) == filenames


@pytest.mark.parametrize("page_index", [0, -3])
def test_page_numbers_below_one_have_no_image_name(page_index):
    """Asking for page 0 or a negative page raises ValueError."""
    with pytest.raises(ValueError, match="start at 1"):
        page_image_filename(page_index)
