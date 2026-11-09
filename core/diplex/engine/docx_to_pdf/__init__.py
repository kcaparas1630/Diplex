"""Converts a DOCX to a PDF with LibreOffice: unoserver_client/ talks to one unoserver, unoserver_pool/ runs the engine's instances."""

from .unoserver_client import (
    DEFAULT_UNOSERVER_PORT,
    DocxConversionError,
    UnoserverUnavailableError,
    convert_docx_to_pdf,
)
from .unoserver_pool import (
    FIRST_UNOSERVER_PORT,
    UnoserverPool,
    UnoserverPoolSettings,
    count_available_cpus,
    unoserver_pool_logger,
)

__all__ = [
    "DEFAULT_UNOSERVER_PORT",
    "FIRST_UNOSERVER_PORT",
    "DocxConversionError",
    "UnoserverPool",
    "UnoserverPoolSettings",
    "UnoserverUnavailableError",
    "convert_docx_to_pdf",
    "count_available_cpus",
    "unoserver_pool_logger",
]
