"""Tests read_page_sizes on the real PDFs in samples/. A test is skipped when its PDF is missing (see samples/SOURCES.md)."""

from pathlib import Path

import pypdfium2
import pytest

from diplex.engine.pages import read_page_sizes

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
US_LETTER = (612.0, 792.0)
BUDGET_PAGE = (630.0, 810.0)  # the US Budget's trim size, 8.75 x 11.25 inches
BUDGET_TURNED_PAGE = (810.0, 630.0)  # the same page with /Rotate 90, as it is shown

# Each page's crop box turned by its /Rotate, as pypdf reads them, so PDFium isn't checked against itself.
EXPECTED_PAGE_SIZES = {
    "irs-form-1040-2025.pdf": [US_LETTER] * 2,
    "un-resolution-78-1-en.pdf": [US_LETTER] * 12,
    "us-budget-fy2025.pdf": [BUDGET_PAGE] * 140 + [BUDGET_TURNED_PAGE] * 40 + [BUDGET_PAGE] * 8,
    "nasa-space-activities-summary-1960.pdf": [  # scanned: each page is the size of its scan
        (607.0, 789.0), (604.0, 787.0), (604.0, 788.0), (594.0, 787.0), (602.0, 787.0), (602.0, 788.0),
        (603.0, 787.0), (603.0, 787.0), (602.0, 787.0), (603.0, 787.0), (603.0, 787.0), (600.0, 786.0),
        (599.0, 787.0), (605.0, 787.0), (605.0, 787.0), (605.0, 787.0), (602.0, 787.0), (601.0, 787.0),
        (602.0, 788.0), (602.0, 787.0), (602.0, 787.0), (598.0, 788.0), (599.0, 787.0), (605.0, 788.0),
        (606.0, 787.0), (603.0, 788.0), (604.0, 789.0), (604.0, 788.0), (605.0, 789.0),
    ],
}


def _sample_pdf_parameters() -> list:
    """One test parameter per PDF in samples/, or a single skipped parameter when there are none."""
    sample_paths = sorted(SAMPLES_FOLDER.glob("*.pdf"))
    if not sample_paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no PDF documents in {SAMPLES_FOLDER}"))]
    return [pytest.param(path, id=path.name) for path in sample_paths]


@pytest.mark.parametrize("sample_path", _sample_pdf_parameters())
def test_every_sample_pdf_gets_one_size_per_page_numbered_from_one(sample_path):
    """Each real PDF gets one size per page, numbered 1, 2, 3, ..., in hundredths of a point."""
    page_sizes = read_page_sizes(sample_path.read_bytes())

    with pypdfium2.PdfDocument(sample_path) as pdf_document:
        page_count = len(pdf_document)
    assert [page_size.index for page_size in page_sizes] == list(range(1, page_count + 1))
    for page_size in page_sizes:
        assert (round(page_size.width, 2), round(page_size.height, 2)) == (page_size.width, page_size.height)


@pytest.mark.parametrize("sample_name", sorted(EXPECTED_PAGE_SIZES))
def test_sample_pdf_pages_have_their_shown_sizes(sample_name):
    """Each page's size is the one it is shown at: scans keep their own sizes and turned pages swap width and height."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")

    page_sizes = read_page_sizes(sample_path.read_bytes())

    assert [(page_size.width, page_size.height) for page_size in page_sizes] == EXPECTED_PAGE_SIZES[sample_name]
