"""Tests that need a running unoserver. Every DOCX in samples/ should become a PDF that keeps its paper sizes, and non-DOCX input should be rejected.

They're skipped if unoserver isn't running (see Commands in AGENTS.md) or samples/ has no DOCX files.
"""

import socket
from pathlib import Path

import pypdfium2
import pytest

from diplex.definition import PageSize
from diplex.engine.docx_to_pdf import DEFAULT_UNOSERVER_PORT, DocxConversionError, convert_docx_to_pdf
from diplex.engine.pages import read_page_sizes

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
PAPER_SIZES_IN_POINTS = {"A4": (595.28, 841.89), "A3": (841.89, 1190.55), "Letter": (612.0, 792.0)}
PAPER_SIZE_TOLERANCE_POINTS = 0.5  # Word and LibreOffice round A4 to twips and hundredths of a mm, e.g. 595.3 wide


def _unoserver_is_listening() -> bool:
    """Tell whether something accepts connections on unoserver's localhost port."""
    try:
        with socket.create_connection(("127.0.0.1", DEFAULT_UNOSERVER_PORT), timeout=3):
            return True
    except OSError:
        return False


def _sample_parameters() -> list:
    """One test parameter per DOCX in samples/, or a single skipped parameter when there are none."""
    sample_paths = sorted(SAMPLES_FOLDER.glob("*.docx"))
    if not sample_paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no DOCX documents in {SAMPLES_FOLDER}"))]
    return [pytest.param(path, id=path.name) for path in sample_paths]


def _paper_size_name(page_size: PageSize) -> str:
    """Name a page's paper size and orientation, like 'A4 landscape', or give its size when it is none of them."""
    for paper_name, (short_side, long_side) in PAPER_SIZES_IN_POINTS.items():
        for orientation, (width, height) in (("portrait", (short_side, long_side)), ("landscape", (long_side, short_side))):
            if (
                abs(page_size.width - width) <= PAPER_SIZE_TOLERANCE_POINTS
                and abs(page_size.height - height) <= PAPER_SIZE_TOLERANCE_POINTS
            ):
                return f"{paper_name} {orientation}"
    return f"{page_size.width} x {page_size.height} pt"


pytestmark = pytest.mark.skipif(
    not _unoserver_is_listening(), reason=f"unoserver is not running on 127.0.0.1:{DEFAULT_UNOSERVER_PORT}"
)


@pytest.mark.parametrize("sample_path", _sample_parameters())
def test_sample_docx_converts_to_a_pdf_with_pages(sample_path):
    """A real DOCX from samples/ comes back as a PDF that opens and has at least one page."""
    pdf_bytes = convert_docx_to_pdf(sample_path.read_bytes())

    assert pdf_bytes.startswith(b"%PDF-")
    pdf_document = pypdfium2.PdfDocument(pdf_bytes)
    try:
        assert len(pdf_document) >= 1
    finally:
        pdf_document.close()


# The paper sizes each sample's sections set in word/document.xml (w:pgSz).
@pytest.mark.parametrize(
    ("sample_name", "expected_paper_sizes"),
    [
        ("defra-air-quality-report-template-2026.docx", {"A4 portrait", "A4 landscape", "A3 landscape"}),
        ("siu-dissertation-template.docx", {"Letter portrait"}),
    ],
    ids=["defra-air-quality-report-template-2026.docx", "siu-dissertation-template.docx"],
)
def test_converted_sample_pages_keep_their_paper_sizes(sample_name, expected_paper_sizes):
    """A converted DOCX's page sizes are the paper sizes its sections set, landscape sections included."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")

    page_sizes = read_page_sizes(convert_docx_to_pdf(sample_path.read_bytes()))

    assert {_paper_size_name(page_size) for page_size in page_sizes} == expected_paper_sizes


@pytest.mark.parametrize("input_bytes", [b"", b"Plain text, not a DOCX.\n"], ids=["empty", "plain-text"])
def test_input_that_is_not_a_docx_is_refused(input_bytes):
    """LibreOffice reads input with the DOCX filter only, so bytes that are not a DOCX are refused, not converted."""
    with pytest.raises(DocxConversionError, match="Could not load document"):
        convert_docx_to_pdf(input_bytes)
