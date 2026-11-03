"""Converts a DOCX to a PDF by sending it to unoserver on localhost.

For now it talks to one unoserver. The pool of unoservers (ADR 004) comes later.
"""

from .unoserver_conversion import (
    DEFAULT_UNOSERVER_PORT,
    DocxConversionError,
    UnoserverUnavailableError,
    convert_docx_to_pdf,
)

__all__ = [
    "DEFAULT_UNOSERVER_PORT",
    "DocxConversionError",
    "UnoserverUnavailableError",
    "convert_docx_to_pdf",
]
