"""Unit tests for the RenderManifest and PageSize contract models: wire format, reading back, and validation."""

import json

import pytest
from pydantic import ValidationError

from diplex.definition import PageSize, RenderManifest

US_LETTER_PAGE = {"width": 612.0, "height": 792.0}
A4_PAGE = {"width": 595.28, "height": 841.89}


def two_page_manifest() -> RenderManifest:
    """A manifest for a two-page document: US Letter, then A4."""
    return RenderManifest(page_count=2, pages=[PageSize(index=1, **US_LETTER_PAGE), PageSize(index=2, **A4_PAGE)])


def test_json_uses_camel_case_keys():
    """On the wire the count is pageCount, and each page is { index, width, height }."""
    wire_json = json.loads(two_page_manifest().model_dump_json())

    assert wire_json == {
        "pageCount": 2,
        "pages": [{"index": 1, **US_LETTER_PAGE}, {"index": 2, **A4_PAGE}],
    }


def test_json_reads_back_into_an_equal_manifest():
    """A manifest survives the round trip through its own JSON unchanged."""
    original = two_page_manifest()

    assert RenderManifest.model_validate_json(original.model_dump_json()) == original


@pytest.mark.parametrize("count_key", ["pageCount", "page_count"])
def test_reads_the_count_by_its_json_or_python_name(count_key):
    """Both pageCount and page_count are accepted when reading a manifest."""
    manifest = RenderManifest.model_validate({count_key: 1, "pages": [{"index": 1, **A4_PAGE}]})

    assert manifest.page_count == 1


def test_the_json_schema_names_the_count_page_count_in_camel_case():
    """The schema FastAPI puts in the OpenAPI spec uses the wire names consumers see."""
    schema = RenderManifest.model_json_schema()

    assert set(schema["properties"]) == {"pageCount", "pages"}
    assert schema["required"] == ["pageCount", "pages"]


@pytest.mark.parametrize(
    "page_indexes",
    [[1], [1, 2, 3], [2, 1], [1, 1], [2, 3]],
    ids=["too-few", "too-many", "out-of-order", "repeated", "not-starting-at-one"],
)
def test_pages_must_match_the_count_in_order(page_indexes):
    """A two-page manifest needs exactly pages 1 and 2, in that order."""
    with pytest.raises(ValidationError, match="numbered 1 to 2 in order"):
        RenderManifest(page_count=2, pages=[PageSize(index=index, **A4_PAGE) for index in page_indexes])


def test_a_document_has_at_least_one_page():
    """A manifest with no pages is rejected."""
    with pytest.raises(ValidationError, match="page_count|pageCount"):
        RenderManifest(page_count=0, pages=[])


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


def test_unknown_fields_are_rejected():
    """Fields outside the contract are refused, so a typo can't slip into the response."""
    with pytest.raises(ValidationError, match="rotation"):
        PageSize.model_validate({"index": 1, **A4_PAGE, "rotation": 90})
