"""Tests render_pdf: page sizes and WebP images from one PDFium pass, under the PDFium lock."""

import io
from pathlib import Path

import pytest
from PIL import Image

from diplex.engine import document_render, render_pdf
from diplex.engine.document_render import PDFIUM_LOCK

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"


def _sample_bytes(sample_name: str) -> bytes:
    """Read a sample PDF, skipping the test when it isn't in samples/."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")
    return sample_path.read_bytes()


def test_a_real_pdf_gives_a_size_and_an_image_per_page():
    """The IRS form gives two US Letter page sizes and two WebP images of 1224 x 1584 px."""
    rendered_document = render_pdf(_sample_bytes("irs-form-1040-2025.pdf"))

    assert [(page.index, page.width, page.height) for page in rendered_document.page_sizes] == [
        (1, 612.0, 792.0),
        (2, 612.0, 792.0),
    ]
    assert [page_webp.filename for page_webp in rendered_document.page_webps] == ["page-0001.webp", "page-0002.webp"]
    for page_webp in rendered_document.page_webps:
        with Image.open(io.BytesIO(page_webp.webp_bytes)) as page_image:
            assert (page_image.format, page_image.size) == ("WEBP", (1224, 1584))


def test_pdfium_is_only_used_while_holding_the_lock(monkeypatch):
    """Every PDFium step runs with the lock held, so two uploads never call PDFium at once."""
    lock_held_during = []

    def fake_read_page_sizes(pdf_bytes):
        """Record whether the lock is held, and return no sizes."""
        lock_held_during.append(("sizes", PDFIUM_LOCK.locked()))
        return []

    def fake_render_page_images(pdf_bytes):
        """Record whether the lock is held while each page renders."""
        for _ in range(2):
            lock_held_during.append(("page", PDFIUM_LOCK.locked()))
            yield Image.new("RGB", (10, 10), "white")

    monkeypatch.setattr(document_render, "read_page_sizes", fake_read_page_sizes)
    monkeypatch.setattr(document_render, "render_page_images", fake_render_page_images)

    render_pdf(b"%PDF-1.7 stand-in")

    assert lock_held_during == [("sizes", True), ("page", True), ("page", True)]
    assert not PDFIUM_LOCK.locked()


def test_the_lock_is_let_go_when_rendering_fails(monkeypatch):
    """A PDF that fails part-way doesn't leave PDFium locked for every later upload."""

    def failing_read_page_sizes(pdf_bytes):
        """Fail as PDFium would on a broken PDF."""
        raise RuntimeError("PDFium failed")

    monkeypatch.setattr(document_render, "read_page_sizes", failing_read_page_sizes)

    with pytest.raises(RuntimeError):
        render_pdf(b"%PDF-1.7 stand-in")
    assert not PDFIUM_LOCK.locked()
