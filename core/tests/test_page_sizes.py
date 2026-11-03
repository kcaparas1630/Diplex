"""Unit tests for read_page_sizes. A fake PDFium stands in when a test needs set page sizes; no PDFs are generated."""

import pypdfium2
import pytest

from diplex.definition import PageSize
from diplex.engine.pages import UnreadablePdfError, read_page_sizes

STAND_IN_PDF = b"%PDF-1.7\n stand-in bytes"
PLAIN_TEXT = b"Plain text, not a PDF.\n"
A4_FROM_PDFIUM = (595.303955078125, 841.8897705078125)  # LibreOffice's A4 page, as PDFium reports it
A4_LANDSCAPE_FROM_PDFIUM = (841.8897705078125, 595.303955078125)
US_LETTER = (612.0, 792.0)
TINY_PAGE_FROM_PDFIUM = (0.004000000189989805, 792.0)  # what PDFium reports for a /MediaBox [0 0 0.004 792]


class FakePdfDocument:
    """Stands in for pypdfium2.PdfDocument: reports set page sizes and records whether it was closed."""

    def __init__(self, page_sizes: list[tuple[float, float]]) -> None:
        """Hold the page sizes to report."""
        self._page_sizes = page_sizes
        self.is_closed = False

    def __enter__(self) -> "FakePdfDocument":
        """Open as a context manager, like the real one."""
        return self

    def __exit__(self, *_) -> None:
        """Close on leaving the with block, like the real one."""
        self.is_closed = True

    def __len__(self) -> int:
        """Return the page count."""
        return len(self._page_sizes)

    def get_page_size(self, page_offset: int) -> tuple[float, float]:
        """Return the size of the page at a zero-based offset."""
        return self._page_sizes[page_offset]


class FakePdfium:
    """Stands in for PDFium: every document it opens reports the page sizes the test sets."""

    def __init__(self) -> None:
        """Start with no pages and no opened documents."""
        self.page_sizes: list[tuple[float, float]] = []
        self.opened_documents: list[FakePdfDocument] = []

    def open_document(self, pdf_bytes: bytes) -> FakePdfDocument:
        """Open a fake document over the set page sizes, ignoring the bytes."""
        pdf_document = FakePdfDocument(self.page_sizes)
        self.opened_documents.append(pdf_document)
        return pdf_document


@pytest.fixture
def fake_pdfium(monkeypatch) -> FakePdfium:
    """Replace pypdfium2.PdfDocument with the fake for one test."""
    pdfium = FakePdfium()
    monkeypatch.setattr(pypdfium2, "PdfDocument", pdfium.open_document)
    return pdfium


def test_rounds_sizes_to_hundredths_of_a_point_and_numbers_pages_from_one(fake_pdfium):
    """PDFium's float32 sizes come back rounded to 0.01 pt, one entry per page, numbered 1, 2, 3 in order."""
    fake_pdfium.page_sizes = [A4_FROM_PDFIUM, A4_LANDSCAPE_FROM_PDFIUM, US_LETTER]

    assert read_page_sizes(STAND_IN_PDF) == [
        PageSize(index=1, width=595.3, height=841.89),
        PageSize(index=2, width=841.89, height=595.3),
        PageSize(index=3, width=612.0, height=792.0),
    ]


def test_closes_the_document_after_reading_the_sizes(fake_pdfium):
    """The PDF is closed once its sizes are read, so a long-running engine doesn't keep documents open."""
    fake_pdfium.page_sizes = [US_LETTER]

    read_page_sizes(STAND_IN_PDF)

    assert [pdf_document.is_closed for pdf_document in fake_pdfium.opened_documents] == [True]


def test_a_page_too_small_to_measure_raises_unreadable(fake_pdfium):
    """A page that rounds to 0 pt raises UnreadablePdfError rather than an invalid page size."""
    fake_pdfium.page_sizes = [US_LETTER, TINY_PAGE_FROM_PDFIUM]

    with pytest.raises(UnreadablePdfError, match="smaller than 0.01 points"):
        read_page_sizes(STAND_IN_PDF)


@pytest.mark.parametrize("input_bytes", [b"", PLAIN_TEXT, STAND_IN_PDF], ids=["empty", "plain-text", "header-only"])
def test_bytes_pdfium_cannot_open_raise_unreadable(input_bytes):
    """Bytes that aren't a whole PDF raise UnreadablePdfError instead of PDFium's own error."""
    with pytest.raises(UnreadablePdfError, match="PDFium could not read the PDF"):
        read_page_sizes(input_bytes)


def test_the_error_does_not_repeat_the_document():
    """The error message leaves out the document's contents, so it is safe to log."""
    with pytest.raises(UnreadablePdfError) as raised:
        read_page_sizes(PLAIN_TEXT)

    assert "Plain text" not in str(raised.value)
