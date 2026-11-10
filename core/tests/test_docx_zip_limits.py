"""Tests the zip-bomb guard on packages made in memory: part count, unzipped size, compression ratio, and lying headers."""

import io
import os
import struct
import zipfile

import pytest

from diplex.engine.checks import DamagedDocxError, DocxLimitsExceededError, check_docx_zip_limits
from diplex.engine.checks import docx_zip_limits

MEBIBYTE = 1024 * 1024


def _package(parts: dict[str, bytes], compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    """A zip holding the given parts."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression) as package:
        for part_name, part_bytes in parts.items():
            package.writestr(part_name, part_bytes)
    return zip_buffer.getvalue()


def test_an_ordinary_package_passes():
    """XML parts and an incompressible image-sized part are within every limit."""
    check_docx_zip_limits(_package({"word/document.xml": b"<w:p>text</w:p>" * 1000, "word/media/image1.png": os.urandom(2 * MEBIBYTE)}))


def test_too_many_parts_are_refused(monkeypatch):
    """More parts than MAX_PART_COUNT is refused from the headers."""
    monkeypatch.setattr(docx_zip_limits, "MAX_PART_COUNT", 10)

    with pytest.raises(DocxLimitsExceededError, match="11 parts, over the limit of 10"):
        check_docx_zip_limits(_package({f"word/part{number}.xml": b"<x/>" for number in range(11)}))


def test_too_many_unzipped_bytes_are_refused(monkeypatch):
    """Parts that add up to more than MAX_UNCOMPRESSED_BYTES are refused, even when each compresses poorly."""
    monkeypatch.setattr(docx_zip_limits, "MAX_UNCOMPRESSED_BYTES", MEBIBYTE)

    with pytest.raises(DocxLimitsExceededError, match="over the limit of 1 MiB"):
        check_docx_zip_limits(_package({"word/media/image1.png": os.urandom(2 * MEBIBYTE)}))


def test_a_large_part_that_expands_too_much_is_refused():
    """A 4 MiB part of zeros deflates over a thousandfold, past the 100 times limit: a zip bomb's signature."""
    with pytest.raises(DocxLimitsExceededError, match="expands .* times, over the limit of 100"):
        check_docx_zip_limits(_package({"word/document.xml": bytes(4 * MEBIBYTE)}))


def test_a_small_part_may_compress_well():
    """Below 1 MiB, a highly compressible part is not a threat and passes."""
    check_docx_zip_limits(_package({"word/styles.xml": bytes(512 * 1024)}))


def test_a_part_whose_headers_understate_its_size_is_damaged():
    """A central directory that claims a part is smaller than it is fails the checksum when read, so it is refused."""
    honest_zip = bytearray(_package({"word/document.xml": b"x" * 4096}, compression=zipfile.ZIP_STORED))
    directory_entry = honest_zip.index(b"PK\x01\x02")
    struct.pack_into("<II", honest_zip, directory_entry + 20, 64, 64)  # compressed and uncompressed size: 64 bytes

    with pytest.raises(DamagedDocxError):
        check_docx_zip_limits(bytes(honest_zip))
