"""The API contract: the Pydantic models and part names for every engine response besides the files (ADR 010).

FastAPI builds the engine's OpenAPI spec from these, and consumers code against that spec (convention 002).
render_manifest holds the JSON part's models, render_parts names every part of the response, and
health_status is the body of GET /health.
"""

from .health_status import HealthStatus
from .render_manifest import PageSize, RenderManifest
from .render_parts import (
    CONVERTED_PDF_FILENAME,
    RENDER_PART_MEDIA_TYPES,
    RenderPart,
    page_image_filename,
)

__all__ = [
    "CONVERTED_PDF_FILENAME",
    "RENDER_PART_MEDIA_TYPES",
    "HealthStatus",
    "PageSize",
    "RenderManifest",
    "RenderPart",
    "page_image_filename",
]
