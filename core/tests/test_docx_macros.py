"""Tests refusing a DOCX that carries macros or ActiveX controls, on packages made in memory (no documents are made)."""

import io
import zipfile

import pytest

from diplex.engine.checks import MacroEnabledDocumentError, reject_macro_enabled_docx

CONTENT_TYPES_START = '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
DOCX_MAIN_OVERRIDE = (
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
)


def _package(extra_declarations: str = "", extra_parts: tuple[str, ...] = ()) -> bytes:
    """A DOCX-shaped zip: [Content_Types].xml with the Word main part, plus the given declarations and empty parts."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as package:
        package.writestr("[Content_Types].xml", CONTENT_TYPES_START + DOCX_MAIN_OVERRIDE + extra_declarations + "</Types>")
        package.writestr("word/document.xml", "<w:document/>")
        for part_name in extra_parts:
            package.writestr(part_name, b"stand-in part")
    return zip_buffer.getvalue()


def test_a_plain_docx_passes():
    """A package with only the Word document part is not refused."""
    reject_macro_enabled_docx(_package())


@pytest.mark.parametrize(
    "declaration",
    [
        '<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>',
        '<Override PartName="/word/vbaData.xml" ContentType="application/vnd.ms-word.vbaData+xml"/>',
        '<Override PartName="/word/activeX/activeX1.xml" ContentType="application/vnd.ms-office.activeX+xml"/>',
        '<Default Extension="bin" ContentType="application/vnd.ms-office.activeX"/>',
    ],
    ids=["vba-project", "vba-data", "activex-xml", "activex-binary"],
)
def test_a_declared_macro_or_activex_type_is_refused(declaration):
    """A VBA project, VBA data or ActiveX content type in [Content_Types].xml is refused."""
    with pytest.raises(MacroEnabledDocumentError, match="macros or ActiveX"):
        reject_macro_enabled_docx(_package(extra_declarations=declaration))


@pytest.mark.parametrize("part_name", ["word/vbaProject.bin", "customXml/VBAPROJECT.BIN", "word/vbaData.xml"])
def test_a_vba_part_is_refused_even_when_undeclared(part_name):
    """A VBA project part hidden without a content type, in any folder or letter case, is refused."""
    with pytest.raises(MacroEnabledDocumentError):
        reject_macro_enabled_docx(_package(extra_parts=(part_name,)))
