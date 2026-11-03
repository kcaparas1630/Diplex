"""The JSON part of a /render response: each page's size in points, in page order (ADR 010).

The page count is the length of pages; it is not sent separately. Every field name is one word, so the
names are the same in Python and in the JSON.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PageSize(BaseModel):
    """One page's number and size in points, so a viewer can lay the page out before its image loads."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1, description="The page's number, counting from 1.")
    width: float = Field(gt=0, description="The page's width in points (1/72 inch).")
    height: float = Field(gt=0, description="The page's height in points (1/72 inch).")


class RenderManifest(BaseModel):
    """Every page's size, first page first; its length is the page count and the number of page images."""

    model_config = ConfigDict(extra="forbid")

    pages: list[PageSize] = Field(min_length=1, description="Every page's size, first page first.")

    @model_validator(mode="after")
    def require_pages_numbered_in_order(self) -> Self:
        """Reject pages that are missing, repeated or out of order, so page N is always pages[N - 1]."""
        expected_indexes = list(range(1, len(self.pages) + 1))
        if [page.index for page in self.pages] != expected_indexes:
            raise ValueError("pages must be numbered 1, 2, 3, ... in order, one entry per page")
        return self
