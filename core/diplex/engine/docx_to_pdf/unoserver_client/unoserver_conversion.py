"""Converts a DOCX to PDF through the unoserver on localhost."""

import http.client
import xmlrpc.client

UNOSERVER_HOST = "127.0.0.1"
DEFAULT_UNOSERVER_PORT = 2003
DEFAULT_TIMEOUT_SECONDS = 120.0  # so a stuck LibreOffice can't block forever
DOCX_IMPORT_FILTER = "MS Word 2007 XML"  # read input as DOCX only, so other formats are rejected
PDF_EXPORT_FILTER = "writer_pdf_Export"
PDF_SIGNATURE = b"%PDF-"


class UnoserverUnavailableError(Exception):
    """unoserver couldn't be reached or dropped the connection."""


class DocxConversionError(Exception):
    """unoserver failed to convert the document or timed out."""


class DocxConversionTimeoutError(DocxConversionError):
    """unoserver did not return the PDF within the conversion timeout."""


class _SingleAttemptTransport(xmlrpc.client.Transport):
    """XML-RPC transport with a timeout and no retry."""

    def __init__(self, timeout_seconds: float) -> None:
        """Return binary results as bytes and store the timeout."""
        super().__init__(use_builtin_types=True)
        self._timeout_seconds = timeout_seconds

    def make_connection(self, host) -> http.client.HTTPConnection:
        """Open the connection with the timeout set."""
        connection = super().make_connection(host)
        connection.timeout = self._timeout_seconds
        return connection

    def request(self, host, handler, request_body, verbose=False):
        """Send the request once, so a document that crashed LibreOffice isn't sent again."""
        return self.single_request(host, handler, request_body, verbose)


def convert_docx_to_pdf(
    docx_bytes: bytes,
    *,
    port: int = DEFAULT_UNOSERVER_PORT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> bytes:
    """Convert a DOCX to PDF with the unoserver on localhost `port`."""
    address = f"http://{UNOSERVER_HOST}:{port}"
    transport = _SingleAttemptTransport(timeout_seconds)
    try:
        with xmlrpc.client.ServerProxy(address, transport=transport, allow_none=True) as unoserver:
            pdf_bytes = unoserver.convert(
                None,  # inpath
                docx_bytes,  # indata
                None,  # outpath: None returns the PDF as bytes
                "pdf",  # convert_to
                PDF_EXPORT_FILTER,  # filtername
                [],  # filter_options
                True,  # update_index: refresh the table of contents page numbers
                DOCX_IMPORT_FILTER,  # infiltername
            )
    except xmlrpc.client.Fault as fault:
        raise DocxConversionError(f"unoserver could not convert the document: {fault.faultString}") from fault
    except TimeoutError as error:
        message = f"LibreOffice did not finish converting the DOCX within {timeout_seconds:g} seconds"
        raise DocxConversionTimeoutError(message) from error
    except (OSError, http.client.HTTPException, xmlrpc.client.ProtocolError) as error:
        raise UnoserverUnavailableError(f"unoserver is not answering on {address}: {error}") from error
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(PDF_SIGNATURE):
        raise DocxConversionError("unoserver answered, but its result is not a PDF")
    return pdf_bytes
