"""Tests the page limit: DIPLEX_MAX_PAGES, checked before any page of a PDF (or the PDF a DOCX became) is rendered."""

import pytest

from diplex.api import create_app
from diplex.api.page_limit_setting import DEFAULT_MAX_PAGES, MAX_PAGES_VARIABLE, read_max_pages
from diplex.definition import PageSize
from diplex.engine import TooManyPagesError, document_render, render_pdf


@pytest.fixture
def three_page_pdf(monkeypatch) -> list[str]:
    """Make PDFium report three pages for any PDF, and record whether any page was rendered."""
    rendered_documents = []
    page_sizes = [PageSize(index=number, width=612.0, height=792.0) for number in (1, 2, 3)]
    monkeypatch.setattr(document_render, "read_page_sizes", lambda pdf_bytes: page_sizes)
    monkeypatch.setattr(document_render, "render_page_images", lambda pdf_bytes: rendered_documents.append(pdf_bytes) or [])
    return rendered_documents


def test_a_pdf_over_the_limit_is_refused_before_any_page_renders(three_page_pdf):
    """Three pages against a limit of two raises TooManyPagesError, and no page image is made."""
    with pytest.raises(TooManyPagesError, match="3 pages, over the limit of 2"):
        render_pdf(b"%PDF-1.7 stand-in", max_pages=2)

    assert three_page_pdf == []


def test_a_pdf_at_the_limit_renders(three_page_pdf):
    """Exactly max_pages pages is allowed."""
    rendered_document = render_pdf(b"%PDF-1.7 stand-in", max_pages=3)

    assert len(rendered_document.page_sizes) == 3


def test_the_default_limit_is_500_pages(monkeypatch):
    """Without DIPLEX_MAX_PAGES the limit is 500 pages (provisional until the engine is measured)."""
    monkeypatch.delenv(MAX_PAGES_VARIABLE, raising=False)

    assert read_max_pages() == DEFAULT_MAX_PAGES == 500


def test_the_limit_comes_from_the_environment(monkeypatch):
    """DIPLEX_MAX_PAGES sets the limit, and the app keeps it."""
    monkeypatch.setenv(MAX_PAGES_VARIABLE, "1200")

    assert read_max_pages() == 1200
    assert create_app().state.max_pages == 1200


@pytest.mark.parametrize("configured_value", ["0", "-3", "lots"])
def test_a_limit_it_cannot_use_stops_the_engine(monkeypatch, configured_value):
    """A zero, negative or non-numeric limit raises ValueError naming the variable when the engine starts."""
    monkeypatch.setenv(MAX_PAGES_VARIABLE, configured_value)

    with pytest.raises(ValueError, match=MAX_PAGES_VARIABLE):
        create_app()
