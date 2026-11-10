"""Tests detect_document_type on the real samples and on non-document input made in memory."""

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from diplex.engine.checks import DocumentType, UnsupportedDocumentError, detect_document_type
from diplex.engine.checks.docx_package import MAX_CONTENT_TYPES_BYTES

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
CONTENT_TYPES_START = '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
MACRO_ENABLED_MAIN_PART_TYPE = "application/vnd.ms-word.document.macroEnabled.main+xml"  # a DOCM
TEMPLATE_MAIN_PART_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"  # a DOTX
SPREADSHEET_MAIN_PART_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"  # an XLSX
BILLION_LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE Types [<!ENTITY a "aaaaaaaaaa">'
    + "".join(f'<!ENTITY {chr(98 + level)} "{("&" + chr(97 + level) + ";") * 10}">' for level in range(9))
    + "]><Types>&j;</Types>"
)


def _sample_parameters(suffix: str) -> list:
    """One test parameter per sample with the suffix, or a single skipped parameter when there are none."""
    sample_paths = sorted(SAMPLES_FOLDER.glob(f"*{suffix}"))
    if not sample_paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no {suffix} documents in {SAMPLES_FOLDER}"))]
    return [pytest.param(path, id=path.name) for path in sample_paths]


def _first_sample_bytes(suffix: str) -> bytes:
    """Read the first sample with the suffix, skipping the test when there is none."""
    sample_paths = sorted(SAMPLES_FOLDER.glob(f"*{suffix}"))
    if not sample_paths:
        pytest.skip(f"no {suffix} documents in {SAMPLES_FOLDER}")
    return sample_paths[0].read_bytes()


def _zip_package(files_by_name: dict[str, str]) -> bytes:
    """Make a zip in memory holding the given text files."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as package:
        for file_name, file_text in files_by_name.items():
            package.writestr(file_name, file_text)
    return zip_buffer.getvalue()


def _package_with_main_part(main_part_type: str) -> bytes:
    """Make a zip whose [Content_Types].xml gives /word/document.xml the main part type."""
    override = f'<Override PartName="/word/document.xml" ContentType="{main_part_type}"/>'
    return _zip_package({"[Content_Types].xml": CONTENT_TYPES_START + override + "</Types>"})


@pytest.mark.parametrize("sample_path", _sample_parameters(".pdf"))
def test_every_sample_pdf_is_a_pdf(sample_path):
    """Each real PDF in samples/ is detected as a PDF."""
    assert detect_document_type(sample_path.read_bytes()) is DocumentType.PDF


@pytest.mark.parametrize("sample_path", _sample_parameters(".docx"))
def test_every_sample_docx_is_a_docx(sample_path):
    """Each real DOCX in samples/ is detected as a DOCX, including the UN ones served with a .DOC name."""
    assert detect_document_type(sample_path.read_bytes()) is DocumentType.DOCX


def test_the_type_values_are_the_ones_consumers_store():
    """The types are docx and pdf, as in the consumer's database (ADR 001 §5)."""
    assert [document_type.value for document_type in DocumentType] == ["docx", "pdf"]


def _png_image_bytes() -> bytes:
    """Encode a small blank image as PNG."""
    png_buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(png_buffer, "PNG")
    return png_buffer.getvalue()


@pytest.mark.parametrize(
    "upload_bytes",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"Plain text, not a document.\n", id="plain-text"),
        pytest.param(b"<html><body>%PDF-1.7</body></html>", id="html-mentioning-a-pdf"),
        pytest.param(_png_image_bytes(), id="png-image"),
        pytest.param(b"PK\x03\x04 not really a zip", id="zip-signature-only"),
        pytest.param(_zip_package({"readme.txt": "hello"}), id="zip-without-content-types"),
        pytest.param(_zip_package({"[Content_Types].xml": "not xml <"}), id="content-types-not-xml"),
        pytest.param(_zip_package({"[Content_Types].xml": BILLION_LAUGHS}), id="content-types-billion-laughs"),
        pytest.param(_package_with_main_part(MACRO_ENABLED_MAIN_PART_TYPE), id="docm-macro-enabled"),
        pytest.param(_package_with_main_part(TEMPLATE_MAIN_PART_TYPE), id="dotx-template"),
        pytest.param(_package_with_main_part(SPREADSHEET_MAIN_PART_TYPE), id="xlsx-spreadsheet"),
    ],
)
def test_non_documents_are_rejected(upload_bytes):
    """Anything that is not a PDF or a DOCX raises UnsupportedDocumentError."""
    with pytest.raises(UnsupportedDocumentError, match="not a PDF or a DOCX"):
        detect_document_type(upload_bytes)


def test_an_oversized_content_types_part_is_not_unzipped_in_full():
    """A [Content_Types].xml over the limit is rejected, though it compresses to a few KB."""
    padding = " " * (MAX_CONTENT_TYPES_BYTES + 1)
    upload_bytes = _zip_package({"[Content_Types].xml": CONTENT_TYPES_START + padding + "</Types>"})

    assert len(upload_bytes) < 10_000
    with pytest.raises(UnsupportedDocumentError):
        detect_document_type(upload_bytes)


def test_a_pdf_with_anything_before_its_signature_is_rejected():
    """The PDF signature must open the file; a real PDF behind other bytes is refused."""
    with pytest.raises(UnsupportedDocumentError):
        detect_document_type(b"junk\n" + _first_sample_bytes(".pdf"))


def test_a_docx_cut_short_is_rejected():
    """A real DOCX missing its second half, where the zip's directory is, is refused."""
    docx_bytes = _first_sample_bytes(".docx")

    with pytest.raises(UnsupportedDocumentError):
        detect_document_type(docx_bytes[: len(docx_bytes) // 2])
