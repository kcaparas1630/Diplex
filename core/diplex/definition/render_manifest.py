"""A successful /render response: its JSON part with each page's size, and its parts by name for the OpenAPI spec."""

from typing import Annotated, Self

from pydantic import BaseModel, Field, WithJsonSchema, model_validator

# OpenAPI 3.1 marks a binary part with contentMediaType; `format: binary` no longer means anything there (OAS 3.1.1 §4.8.14.3).
WebpImagePart = Annotated[bytes, WithJsonSchema({"type": "string", "contentMediaType": "image/webp"})]
# Optional: a PDF upload's response has no pdf part at all, rather than an empty one.
OptionalPdfFilePart = Annotated[bytes | None, WithJsonSchema({"type": "string", "contentMediaType": "application/pdf"})]


class PageSize(BaseModel):
    """A page's number and size in points."""

    index: int = Field(ge=1, description="Page number, from 1.")
    width: float = Field(gt=0, description="Width in points as the page is shown (rotation applied), to 0.01 pt.")
    height: float = Field(gt=0, description="Height in points as the page is shown (rotation applied), to 0.01 pt.")


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


class RenderResponseParts(BaseModel):
    """A successful /render response's multipart/form-data parts, by name: what `await response.formData()` holds."""

    manifest: RenderManifest = Field(
        description="JSON part, sent first, with no file name, so formData().get('manifest') is a string to JSON.parse."
    )
    page: list[WebpImagePart] = Field(
        description="One lossless WebP per page, in page order, every part named page; "
        "file names page-0001.webp, page-0002.webp, ... Read them with formData().getAll('page')."
    )
    pdf: OptionalPdfFilePart = Field(
        default=None,
        description="Only for a DOCX upload: the PDF it was converted to, named document.pdf.",
        json_schema_extra=lambda field_schema: field_schema.pop("default", None),  # absent, not null
    )
