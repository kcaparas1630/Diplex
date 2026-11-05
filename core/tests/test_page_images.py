"""Unit tests for render_page_images. A fake PDFium records what is opened, rendered and freed; no PDFs are generated."""

import math

import pypdfium2
import pytest
from PIL import Image

from diplex.engine.pages import PageTooLargeError, UnreadablePdfError, render_page_images
from diplex.engine.pages.page_images import MAX_PAGE_PIXELS, MAX_PAGE_SIDE_PIXELS

STAND_IN_PDF = b"%PDF-1.7\n stand-in bytes"
US_LETTER = (612.0, 792.0)
A4_FROM_PDFIUM = (595.303955078125, 841.8897705078125)  # LibreOffice's A4 page, as PDFium reports it
A0_DRAWING = (2383.94, 3370.39)  # 4768 x 6741 px at 144 DPI: 32 MP, under the limit
TOO_LARGE_PAGE = (14400.0, 14400.0)  # the PDF spec's 200-inch maximum: 28800 x 28800 px at 144 DPI
LONGEST_PAGE = (612.0, 8191.5)  # 8.5 x 113.77 inches: 1224 x 16383 px, WebP's longest side
TOO_LONG_PAGE = (612.0, 8200.0)  # a long receipt: 1224 x 16400 px is only 20 MP, but too tall for WebP


class FakeBitmap:
    """Stands in for a pypdfium2 bitmap: hands out a blank image of its size and records being freed."""

    def __init__(self, events: list[str], page_number: int, pixel_size: tuple[int, int]) -> None:
        """Hold the shared event log, the page number and the size in pixels."""
        self._events = events
        self._page_number = page_number
        self._pixel_size = pixel_size

    def to_pil(self) -> Image.Image:
        """Return a blank RGB image of the bitmap's size."""
        return Image.new("RGB", self._pixel_size, "white")

    def close(self) -> None:
        """Record that the bitmap was freed."""
        self._events.append(f"free bitmap {self._page_number}")


class FakePage:
    """Stands in for a pypdfium2 page: records rendering and being closed."""

    def __init__(self, events: list[str], page_number: int, page_size: tuple[float, float], failing: bool) -> None:
        """Hold the shared event log, the page's number and size, and whether rendering should fail."""
        self._events = events
        self._page_number = page_number
        self._page_size = page_size
        self._failing = failing

    def render(self, scale: float) -> FakeBitmap:
        """Record the scale and return a bitmap sized the way pypdfium2 sizes it, or raise PDFium's error."""
        self._events.append(f"render page {self._page_number} at scale {scale}")
        if self._failing:
            raise pypdfium2.PdfiumError("Failed to render page.")
        width, height = self._page_size
        return FakeBitmap(self._events, self._page_number, (math.ceil(width * scale), math.ceil(height * scale)))

    def close(self) -> None:
        """Record that the page was closed."""
        self._events.append(f"close page {self._page_number}")


class FakePdfDocument:
    """Stands in for pypdfium2.PdfDocument over set page sizes, recording every call in order."""

    def __init__(self, events: list[str], page_sizes: list[tuple[float, float]], failing_page_number: int) -> None:
        """Hold the shared event log, the page sizes, and which page (if any) fails to render."""
        self._events = events
        self._page_sizes = page_sizes
        self._failing_page_number = failing_page_number

    def __enter__(self) -> "FakePdfDocument":
        """Open as a context manager, like the real one."""
        return self

    def __exit__(self, *_) -> None:
        """Record closing on leaving the with block."""
        self._events.append("close document")

    def init_forms(self) -> None:
        """Record that form drawing was set up."""
        self._events.append("init forms")

    def __len__(self) -> int:
        """Return the page count."""
        return len(self._page_sizes)

    def get_page_size(self, page_offset: int) -> tuple[float, float]:
        """Return a page's size in points without opening it."""
        return self._page_sizes[page_offset]

    def __getitem__(self, page_offset: int) -> FakePage:
        """Open the page at a zero-based offset."""
        page_number = page_offset + 1
        self._events.append(f"open page {page_number}")
        failing = page_number == self._failing_page_number
        return FakePage(self._events, page_number, self._page_sizes[page_offset], failing)


class FakePdfium:
    """Stands in for PDFium: opens fake documents over the page sizes the test sets."""

    def __init__(self) -> None:
        """Start with no pages, no failing page and an empty event log."""
        self.page_sizes: list[tuple[float, float]] = []
        self.failing_page_number = 0
        self.events: list[str] = []

    def open_document(self, pdf_bytes: bytes) -> FakePdfDocument:
        """Open a fake document, ignoring the bytes."""
        self.events.append("open document")
        return FakePdfDocument(self.events, self.page_sizes, self.failing_page_number)


@pytest.fixture
def fake_pdfium(monkeypatch) -> FakePdfium:
    """Replace pypdfium2.PdfDocument with the fake for one test."""
    pdfium = FakePdfium()
    monkeypatch.setattr(pypdfium2, "PdfDocument", pdfium.open_document)
    return pdfium


def test_renders_at_two_pixels_per_point(fake_pdfium):
    """144 DPI over 72 points to the inch is a scale of 2: Letter becomes 1224 x 1584 px, A4 rounds up to 1191 x 1684."""
    fake_pdfium.page_sizes = [US_LETTER, A4_FROM_PDFIUM]

    page_images = list(render_page_images(STAND_IN_PDF))

    assert [page_image.size for page_image in page_images] == [(1224, 1584), (1191, 1684)]
    assert "render page 1 at scale 2" in fake_pdfium.events


def test_renders_a_page_only_when_it_is_asked_for_and_frees_it_first(fake_pdfium):
    """Each page is opened, rendered and freed before it is handed over, and the next waits until it is asked for."""
    fake_pdfium.page_sizes = [US_LETTER, US_LETTER]
    page_images = render_page_images(STAND_IN_PDF)

    next(page_images)
    assert fake_pdfium.events == [
        "open document",
        "init forms",
        "open page 1",
        "render page 1 at scale 2",
        "free bitmap 1",
        "close page 1",
    ]

    next(page_images)
    assert fake_pdfium.events[-4:] == ["open page 2", "render page 2 at scale 2", "free bitmap 2", "close page 2"]


def test_stopping_early_closes_the_document(fake_pdfium):
    """A caller that stops after the first page still gets the document closed."""
    fake_pdfium.page_sizes = [US_LETTER, US_LETTER, US_LETTER]
    page_images = render_page_images(STAND_IN_PDF)

    next(page_images)
    page_images.close()

    assert fake_pdfium.events[-1] == "close document"
    assert "open page 2" not in fake_pdfium.events


def test_an_a0_drawing_is_under_the_pixel_limit(fake_pdfium):
    """The largest standard paper size renders: an A0 page is 4768 x 6741 px."""
    fake_pdfium.page_sizes = [A0_DRAWING]

    assert [page_image.size for page_image in render_page_images(STAND_IN_PDF)] == [(4768, 6741)]
    assert 4768 * 6741 < MAX_PAGE_PIXELS


def test_a_page_too_large_is_refused_before_any_page_renders(fake_pdfium):
    """A page over the pixel limit raises PageTooLargeError before the first page is opened, wherever it is."""
    fake_pdfium.page_sizes = [US_LETTER, TOO_LARGE_PAGE]

    with pytest.raises(PageTooLargeError, match="page 2 would render at 28800 x 28800 pixels"):
        next(render_page_images(STAND_IN_PDF))
    assert not any(event.startswith("open page") for event in fake_pdfium.events)
    assert fake_pdfium.events[-1] == "close document"


def test_a_page_as_long_as_webp_allows_renders(fake_pdfium):
    """A page 16383 px long, WebP's limit, renders."""
    fake_pdfium.page_sizes = [LONGEST_PAGE]

    assert [page_image.size for page_image in render_page_images(STAND_IN_PDF)] == [(1224, MAX_PAGE_SIDE_PIXELS)]


def test_a_page_longer_than_webp_allows_is_refused_before_any_page_renders(fake_pdfium):
    """A page under the pixel limit but over 16383 px on a side raises PageTooLargeError before the first page is opened."""
    fake_pdfium.page_sizes = [US_LETTER, TOO_LONG_PAGE]

    with pytest.raises(PageTooLargeError, match="page 2 would render at 1224 x 16400 pixels, over WebP's limit"):
        next(render_page_images(STAND_IN_PDF))
    assert 1224 * 16400 < MAX_PAGE_PIXELS
    assert not any(event.startswith("open page") for event in fake_pdfium.events)


def test_a_page_pdfium_cannot_render_raises_unreadable(fake_pdfium):
    """PDFium failing on a page raises UnreadablePdfError instead of PDFium's own error, and the page is closed."""
    fake_pdfium.page_sizes = [US_LETTER, US_LETTER]
    fake_pdfium.failing_page_number = 2
    page_images = render_page_images(STAND_IN_PDF)
    next(page_images)

    with pytest.raises(UnreadablePdfError, match="PDFium could not render the PDF"):
        next(page_images)
    assert fake_pdfium.events[-2:] == ["close page 2", "close document"]


@pytest.mark.parametrize("input_bytes", [b"", b"Plain text, not a PDF.\n", STAND_IN_PDF], ids=["empty", "plain-text", "header-only"])
def test_bytes_pdfium_cannot_open_raise_unreadable(input_bytes):
    """Bytes that aren't a whole PDF raise UnreadablePdfError when the first page is asked for."""
    with pytest.raises(UnreadablePdfError, match="PDFium could not read the PDF"):
        next(render_page_images(input_bytes))
