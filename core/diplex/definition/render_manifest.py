"""The JSON part of a /render response: the page count and each page's size in points (ADR 010).

Fields are snake_case in Python and camelCase on the wire (`pageCount`), the usual style for JSON read by
JavaScript. Either spelling is accepted when the JSON is read back.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

CONTRACT_MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    validate_by_name=True,
    validate_by_alias=True,
    serialize_by_alias=True,
    extra="forbid",
)


class PageSize(BaseModel):
    """One page's number and size in points, so a viewer can lay the page out before its image loads."""

    model_config = CONTRACT_MODEL_CONFIG

    index: int = Field(ge=1, description="The page's number, counting from 1.")
    width: float = Field(gt=0, description="The page's width in points (1/72 inch).")
    height: float = Field(gt=0, description="The page's height in points (1/72 inch).")


class RenderManifest(BaseModel):
    """How many pages the rendered document has, and each page's size in page order."""

    model_config = CONTRACT_MODEL_CONFIG

    page_count: int = Field(ge=1, description="The number of pages, which is also the number of page images.")
    pages: list[PageSize] = Field(description="Every page's size, first page first.")

    @model_validator(mode="after")
    def require_one_size_per_page_in_order(self) -> Self:
        """Reject pages that are missing, repeated or out of order, so page N is always pages[N - 1]."""
        expected_indexes = list(range(1, self.page_count + 1))
        if [page.index for page in self.pages] != expected_indexes:
            raise ValueError(f"pages must be numbered 1 to {self.page_count} in order, one entry per page")
        return self
