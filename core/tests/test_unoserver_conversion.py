"""Unit tests for convert_docx_to_pdf. They use fake servers on localhost, so LibreOffice isn't needed."""

import socket
import threading
import xmlrpc.server
from collections.abc import Iterator

import pytest

from diplex.engine.docx_to_pdf import (
    DEFAULT_UNOSERVER_PORT,
    DocxConversionError,
    UnoserverUnavailableError,
    convert_docx_to_pdf,
)

STAND_IN_DOCX = b"PK\x03\x04 stand-in DOCX bytes"
STAND_IN_PDF = b"%PDF-1.7\n stand-in PDF bytes"
DROPPED_CONNECTION = b""
HTTP_SERVER_ERROR = b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"


class FakeUnoserver:
    """A stand-in unoserver on 127.0.0.1 that records each convert call and answers as the test sets."""

    def __init__(self) -> None:
        """Start an XML-RPC server on a free localhost port in a background thread."""
        self.received_calls: list[tuple] = []
        self.reply: bytes | Exception = STAND_IN_PDF
        self.reply_delay_seconds = 0.0
        self._release_reply = threading.Event()
        self._server = xmlrpc.server.SimpleXMLRPCServer(
            ("127.0.0.1", 0), allow_none=True, logRequests=False, use_builtin_types=True
        )
        self._server.register_function(self._convert, "convert")
        self.port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def _convert(self, *arguments):
        """Record the call, hold the reply if asked to, then return it, or raise it so it becomes a fault."""
        self.received_calls.append(arguments)
        self._release_reply.wait(self.reply_delay_seconds)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply

    def stop(self) -> None:
        """Release any held reply, then shut the server down."""
        self._release_reply.set()
        self._server.shutdown()
        self._server.server_close()


class CannedReplyServer:
    """A localhost server that reads each request, sends fixed bytes back (none to just hang up) and closes."""

    def __init__(self, canned_reply: bytes) -> None:
        """Start listening on a free localhost port and serve connections in a background thread."""
        self.connection_count = 0
        self._canned_reply = canned_reply
        self._stopped = threading.Event()
        self._listener = socket.create_server(("127.0.0.1", 0))
        self._listener.settimeout(0.1)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        """Accept connections until stopped, answering each once its whole request has arrived."""
        while not self._stopped.is_set():
            try:
                connection, _ = self._listener.accept()
            except TimeoutError:
                continue
            self.connection_count += 1
            with connection:
                connection.settimeout(5)
                received = b""
                while b"</methodCall>" not in received:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    received += chunk
                connection.sendall(self._canned_reply)

    def stop(self) -> None:
        """Stop accepting connections, wait for the serving thread to finish, then close the listening socket."""
        self._stopped.set()
        self._thread.join()
        self._listener.close()


@pytest.fixture
def fake_unoserver() -> Iterator[FakeUnoserver]:
    """A running stand-in unoserver, stopped after the test."""
    server = FakeUnoserver()
    yield server
    server.stop()


@pytest.fixture
def closed_port() -> int:
    """A localhost port that nothing listens on."""
    with socket.create_server(("127.0.0.1", 0)) as probe:
        return probe.getsockname()[1]


def test_sends_the_docx_bytes_with_fixed_filters_and_returns_the_pdf(fake_unoserver):
    """The DOCX reaches unoserver as bytes with the DOCX import and PDF export filters; the PDF comes back."""
    pdf_bytes = convert_docx_to_pdf(STAND_IN_DOCX, port=fake_unoserver.port)

    assert pdf_bytes == STAND_IN_PDF
    assert fake_unoserver.received_calls == [
        (None, STAND_IN_DOCX, None, "pdf", "writer_pdf_Export", [], True, "MS Word 2007 XML"),
    ]


def test_uses_unoservers_standard_port_by_default():
    """Without a port, the conversion goes to unoserver's default XML-RPC port, 2003."""
    assert DEFAULT_UNOSERVER_PORT == 2003


def test_a_fault_from_unoserver_raises_a_conversion_error_with_its_message(fake_unoserver):
    """unoserver failing on the document raises DocxConversionError carrying unoserver's message."""
    fake_unoserver.reply = RuntimeError("Could not load document <remote file> using the MS Word 2007 XML filter.")

    with pytest.raises(DocxConversionError, match="Could not load document"):
        convert_docx_to_pdf(STAND_IN_DOCX, port=fake_unoserver.port)


def test_a_reply_that_is_not_a_pdf_raises_a_conversion_error(fake_unoserver):
    """Bytes without the PDF signature are refused rather than passed on as a PDF."""
    fake_unoserver.reply = b"<html>not a PDF</html>"

    with pytest.raises(DocxConversionError, match="not a PDF"):
        convert_docx_to_pdf(STAND_IN_DOCX, port=fake_unoserver.port)


def test_a_conversion_slower_than_the_timeout_raises_a_conversion_error(fake_unoserver):
    """A conversion that outlasts timeout_seconds raises DocxConversionError instead of waiting on."""
    fake_unoserver.reply_delay_seconds = 10

    with pytest.raises(DocxConversionError, match="within 0.3 seconds"):
        convert_docx_to_pdf(STAND_IN_DOCX, port=fake_unoserver.port, timeout_seconds=0.3)


def test_nothing_listening_on_the_port_raises_unavailable(closed_port):
    """No unoserver on the port raises UnoserverUnavailableError."""
    with pytest.raises(UnoserverUnavailableError, match=f"127.0.0.1:{closed_port}"):
        convert_docx_to_pdf(STAND_IN_DOCX, port=closed_port)


def test_a_dropped_connection_raises_unavailable_without_resending_the_document():
    """unoserver hanging up mid-request raises UnoserverUnavailableError, and the DOCX is sent only once."""
    server = CannedReplyServer(DROPPED_CONNECTION)
    try:
        with pytest.raises(UnoserverUnavailableError):
            convert_docx_to_pdf(STAND_IN_DOCX, port=server.port)
        assert server.connection_count == 1
    finally:
        server.stop()


def test_an_http_error_from_the_port_raises_unavailable():
    """Something other than a working unoserver answering with an HTTP error raises UnoserverUnavailableError."""
    server = CannedReplyServer(HTTP_SERVER_ERROR)
    try:
        with pytest.raises(UnoserverUnavailableError, match="500"):
            convert_docx_to_pdf(STAND_IN_DOCX, port=server.port)
    finally:
        server.stop()
