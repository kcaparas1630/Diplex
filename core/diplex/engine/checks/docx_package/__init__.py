"""Reads what a DOCX package declares about itself: the content types in [Content_Types].xml and its part names."""

from .content_types import MAX_CONTENT_TYPES_BYTES, list_part_names, read_part_content_types

__all__ = ["MAX_CONTENT_TYPES_BYTES", "list_part_names", "read_part_content_types"]
