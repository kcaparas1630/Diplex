"""Refuses a DOCX that carries macros or ActiveX controls before LibreOffice opens it (convention 003)."""

from pathlib import PurePosixPath

from .docx_package import list_part_names, read_part_content_types

# Content types Word declares for VBA projects, their data and signatures, and ActiveX controls.
ACTIVE_CONTENT_TYPE_MARKERS = ("vnd.ms-office.vba", "vnd.ms-word.vbadata", "vnd.ms-office.activex", "macroenabled")
# Part names Word gives a VBA project and its data, wherever a package puts them.
ACTIVE_PART_NAMES = frozenset({"vbaproject.bin", "vbadata.xml", "vbaprojectsignature.bin"})


class MacroEnabledDocumentError(Exception):
    """The DOCX carries a VBA project, its data or ActiveX controls."""


def reject_macro_enabled_docx(docx_bytes: bytes) -> None:
    """Raise MacroEnabledDocumentError if the package declares or contains macro or ActiveX parts."""
    part_content_types = read_part_content_types(docx_bytes) or []
    if any(marker in content_type.lower() for content_type in part_content_types for marker in ACTIVE_CONTENT_TYPE_MARKERS):
        raise MacroEnabledDocumentError("the DOCX carries macros or ActiveX controls, which the engine does not convert")
    part_names = list_part_names(docx_bytes) or []
    if any(PurePosixPath(part_name).name.lower() in ACTIVE_PART_NAMES for part_name in part_names):
        raise MacroEnabledDocumentError("the DOCX carries macros or ActiveX controls, which the engine does not convert")
