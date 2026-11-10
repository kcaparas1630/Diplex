"""Reads a DOCX package's [Content_Types].xml, which lists the type of every part, without unzipping more than it needs."""

import io
import lzma
import zipfile
import zlib
from xml.etree import ElementTree

CONTENT_TYPES_PART = "[Content_Types].xml"  # every Office Open XML package lists its parts' types here
CONTENT_TYPES_NAMESPACE = "{http://schemas.openxmlformats.org/package/2006/content-types}"
MAX_CONTENT_TYPES_BYTES = 1_000_000  # a real one is a few KB; never unzip more than this to read it
UNREADABLE_ZIP_ERRORS = (
    zipfile.BadZipFile,  # not a zip, or a damaged one
    KeyError,  # no [Content_Types].xml
    RuntimeError,  # encrypted
    NotImplementedError,  # an unknown compression method
    EOFError,  # cut short
    OSError,  # damaged bzip2 data
    zlib.error,  # damaged deflate data
    lzma.LZMAError,  # damaged LZMA data
)


def read_part_content_types(zip_bytes: bytes) -> list[str] | None:
    """Every content type [Content_Types].xml declares (Default and Override), or None if it can't be read."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as package, package.open(CONTENT_TYPES_PART) as content_types_file:
            content_types_xml = content_types_file.read(MAX_CONTENT_TYPES_BYTES + 1)
    except UNREADABLE_ZIP_ERRORS:
        return None
    if len(content_types_xml) > MAX_CONTENT_TYPES_BYTES:
        return None
    try:
        content_types = ElementTree.fromstring(content_types_xml)  # safe with Expat 2.7.2 or later (Python's XML docs)
    except ElementTree.ParseError:
        return None
    declarations = [*content_types.iter(f"{CONTENT_TYPES_NAMESPACE}Default"), *content_types.iter(f"{CONTENT_TYPES_NAMESPACE}Override")]
    return [declaration.get("ContentType", "") for declaration in declarations]


def list_part_names(zip_bytes: bytes) -> list[str] | None:
    """The names of every part in the zip's central directory, or None if it isn't a readable zip."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as package:
            return package.namelist()
    except UNREADABLE_ZIP_ERRORS:
        return None
