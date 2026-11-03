"""Tests that need a running unoserver. Every DOCX in samples/ should become a PDF, and non-DOCX input should be rejected.

They're skipped if unoserver isn't running (see Commands in AGENTS.md) or samples/ has no DOCX files.
"""

import socket
from pathlib import Path

import pypdfium2
import pytest

from diplex_core.engine.docx_to_pdf import DEFAULT_UNOSERVER_PORT, DocxConversionError, convert_docx_to_pdf

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"


def _unoserver_is_listening() -> bool:
    """Tell whether something accepts connections on unoserver's localhost port."""
    try:
        with socket.create_connection(("127.0.0.1", DEFAULT_UNOSERVER_PORT), timeout=3):
            return True
    except OSError:
        return False


def _sample_parameters() -> list:
    """One test parameter per DOCX in samples/, or a single skipped parameter when there are none."""
    sample_paths = sorted(SAMPLES_FOLDER.glob("*.docx"))
    if not sample_paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no DOCX documents in {SAMPLES_FOLDER}"))]
    return [pytest.param(path, id=path.name) for path in sample_paths]


pytestmark = pytest.mark.skipif(
    not _unoserver_is_listening(), reason=f"unoserver is not running on 127.0.0.1:{DEFAULT_UNOSERVER_PORT}"
)


@pytest.mark.parametrize("sample_path", _sample_parameters())
def test_sample_docx_converts_to_a_pdf_with_pages(sample_path):
    """A real DOCX from samples/ comes back as a PDF that opens and has at least one page."""
    pdf_bytes = convert_docx_to_pdf(sample_path.read_bytes())

    assert pdf_bytes.startswith(b"%PDF-")
    pdf_document = pypdfium2.PdfDocument(pdf_bytes)
    try:
        assert len(pdf_document) >= 1
    finally:
        pdf_document.close()


@pytest.mark.parametrize("input_bytes", [b"", b"Plain text, not a DOCX.\n"], ids=["empty", "plain-text"])
def test_input_that_is_not_a_docx_is_refused(input_bytes):
    """LibreOffice reads input with the DOCX filter only, so bytes that are not a DOCX are refused, not converted."""
    with pytest.raises(DocxConversionError, match="Could not load document"):
        convert_docx_to_pdf(input_bytes)
