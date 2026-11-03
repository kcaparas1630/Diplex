"""The JSON part of a /render response: each page's size in points."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class PageSize(BaseModel):
    """A page's number and size in points."""

    index: int = Field(ge=1, description="Page number, from 1.")
    width: float = Field(gt=0, description="Width in points.")
    height: float = Field(gt=0, description="Height in points.")


class RenderManifest(BaseModel):
    """Every page's size in page order; its length is the page count."""

    pages: list[PageSize] = Field(min_length=1, description="Each page's size, first page first.")

    @model_validator(mode="after")
    def require_pages_numbered_in_order(self) -> Self:
        """Require pages numbered 1, 2, 3, ... in order."""
        expected_indexes = list(range(1, len(self.pages) + 1))
        if [page.index for page in self.pages] != expected_indexes:
            raise ValueError("pages must be numbered 1, 2, 3, ... in order, one entry per page")
        return self
