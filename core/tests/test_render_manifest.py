"""Unit tests for the RenderManifest and PageSize contract models: wire format, reading back, and validation."""

import json

import pytest
from pydantic import ValidationError

from diplex.definition import PageSize, RenderManifest

US_LETTER_PAGE = {"width": 612.0, "height": 792.0}
A4_PAGE = {"width": 595.28, "height": 841.89}


def two_page_manifest() -> RenderManifest:
    """A manifest for a two-page document: US Letter, then A4."""
    return RenderManifest(pages=[PageSize(index=1, **US_LETTER_PAGE), PageSize(index=2, **A4_PAGE)])


def test_json_is_the_list_of_pages_and_nothing_else():
    """On the wire the manifest is { pages: [{ index, width, height }, ...] }; the count is pages.length."""
    wire_json = json.loads(two_page_manifest().model_dump_json())

    assert wire_json == {"pages": [{"index": 1, **US_LETTER_PAGE}, {"index": 2, **A4_PAGE}]}
    assert len(wire_json["pages"]) == 2


def test_json_reads_back_into_an_equal_manifest():
    """A manifest survives the round trip through its own JSON unchanged."""
    original = two_page_manifest()

    assert RenderManifest.model_validate_json(original.model_dump_json()) == original


def test_the_json_schema_requires_at_least_one_page():
    """The schema FastAPI puts in the OpenAPI spec has only pages, with at least one entry."""
    schema = RenderManifest.model_json_schema()

    assert set(schema["properties"]) == {"pages"}
    assert schema["required"] == ["pages"]
    assert schema["properties"]["pages"]["minItems"] == 1


@pytest.mark.parametrize(
    "page_indexes",
    [[2, 1], [1, 1], [2, 3], [1, 3]],
    ids=["out-of-order", "repeated", "not-starting-at-one", "gap"],
)
def test_pages_are_numbered_from_one_in_order(page_indexes):
    """Pages must be numbered 1, 2, 3, ... with nothing missing, repeated or out of order."""
    with pytest.raises(ValidationError, match="numbered 1, 2, 3"):
        RenderManifest(pages=[PageSize(index=index, **A4_PAGE) for index in page_indexes])


def test_a_document_has_at_least_one_page():
    """A manifest with no pages is rejected."""
    with pytest.raises(ValidationError, match="at least 1 item"):
        RenderManifest(pages=[])


@pytest.mark.parametrize("page_number", [0, -1])
def test_page_numbers_start_at_one(page_number):
    """Page numbers below 1 are rejected."""
    with pytest.raises(ValidationError, match="index"):
        PageSize(index=page_number, **A4_PAGE)


@pytest.mark.parametrize("bad_size", [{"width": 0.0, "height": 792.0}, {"width": 612.0, "height": -1.0}])
def test_page_sizes_are_positive(bad_size):
    """A page with no width or a negative height is rejected."""
    with pytest.raises(ValidationError, match="greater than 0"):
        PageSize(index=1, **bad_size)


def test_a_separate_page_count_is_rejected():
    """The count is pages.length, so a pageCount field is refused rather than silently ignored."""
    with pytest.raises(ValidationError, match="pageCount"):
        RenderManifest.model_validate({"pages": [{"index": 1, **A4_PAGE}], "pageCount": 1})


def test_unknown_page_fields_are_rejected():
    """Fields outside the contract are refused, so a typo can't slip into the response."""
    with pytest.raises(ValidationError, match="rotation"):
        PageSize.model_validate({"index": 1, **A4_PAGE, "rotation": 90})
