"""Tests how the pool hands out conversions, with the stand-in unoserver: one per idle instance, waiting, busy, down."""

import sys
import threading
import time
from pathlib import Path

import pytest

from diplex.engine import (
    ConverterBusyError,
    DocxConversionError,
    InstanceState,
    UnoserverPool,
    UnoserverPoolSettings,
    UnoserverUnavailableError,
)
from diplex.engine.docx_to_pdf.unoserver_pool import unoserver_pool as unoserver_pool_module
from localhost_ports import find_free_port_range

STAND_IN_UNOSERVER = (sys.executable, str(Path(__file__).with_name("stand_in_unoserver.py")))
INSTANCE_START_SECONDS = 10


def _started_pool(instance_count: int, wait_seconds: float = 10) -> UnoserverPool:
    """Start a pool of stand-in instances on free ports and wait until every one is idle."""
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(
            instance_count=instance_count,
            wait_seconds=wait_seconds,
            first_port=find_free_port_range(2 * instance_count),
            unoserver_command=STAND_IN_UNOSERVER,
        )
    )
    unoserver_pool.start()
    deadline = time.monotonic() + INSTANCE_START_SECONDS
    while any(pooled_instance.state is not InstanceState.IDLE for pooled_instance in unoserver_pool.instances):
        if time.monotonic() > deadline:
            unoserver_pool.stop()
            raise AssertionError("the stand-in instances did not become idle")
        time.sleep(0.02)
    return unoserver_pool


def _convert_at_once(unoserver_pool: UnoserverPool, documents: list[bytes]) -> list[bytes | Exception]:
    """Convert every document on its own thread, all at once, and return each PDF or error in document order."""
    outcomes: list[bytes | Exception] = [b""] * len(documents)

    def convert_one(document_index: int) -> None:
        """Convert one document and keep its PDF or its error."""
        try:
            outcomes[document_index] = unoserver_pool.convert_docx_to_pdf(documents[document_index])
        except Exception as error:
            outcomes[document_index] = error

    threads = [threading.Thread(target=convert_one, args=(document_index,)) for document_index in range(len(documents))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return outcomes


@pytest.fixture
def conversion_time(monkeypatch):
    """Make every stand-in conversion take the given number of seconds."""
    return lambda seconds: monkeypatch.setenv("STAND_IN_UNOSERVER_CONVERT_SECONDS", str(seconds))


def test_concurrent_conversions_each_get_their_own_idle_instance(conversion_time):
    """Three conversions at once on three instances run side by side, one per instance."""
    conversion_time(1)
    unoserver_pool = _started_pool(instance_count=3)
    try:
        started = time.monotonic()
        outcomes = _convert_at_once(unoserver_pool, [b"PK one", b"PK two", b"PK three"])
        elapsed_seconds = time.monotonic() - started
    finally:
        unoserver_pool.stop()

    assert all(isinstance(outcome, bytes) for outcome in outcomes), outcomes
    assert len(set(outcomes)) == 3  # each PDF names the instance that converted it
    assert elapsed_seconds < 2.5  # side by side, not one after another (3 s)


def test_an_instance_never_converts_two_documents_at_once(conversion_time, monkeypatch):
    """Eight conversions on two instances: every one succeeds, both instances work, and none overlaps on one instance."""
    conversion_time(0.1)
    calls_by_port: dict[int, list[tuple[float, float]]] = {}
    calls_lock = threading.Lock()
    real_conversion = unoserver_pool_module.convert_docx_to_pdf

    def timed_conversion(docx_bytes, port):
        """Convert as the pool would, recording when the call to each port started and ended."""
        call_started = time.monotonic()
        pdf_bytes = real_conversion(docx_bytes, port=port)
        with calls_lock:
            calls_by_port.setdefault(port, []).append((call_started, time.monotonic()))
        return pdf_bytes

    monkeypatch.setattr(unoserver_pool_module, "convert_docx_to_pdf", timed_conversion)
    unoserver_pool = _started_pool(instance_count=2)
    try:
        outcomes = _convert_at_once(unoserver_pool, [b"PK document %d" % number for number in range(8)])
    finally:
        unoserver_pool.stop()

    assert all(isinstance(outcome, bytes) for outcome in outcomes), outcomes
    assert len(calls_by_port) == 2
    for calls in calls_by_port.values():
        ordered_calls = sorted(calls)
        for (_, earlier_end), (later_start, _) in zip(ordered_calls, ordered_calls[1:]):
            assert later_start >= earlier_end


def test_a_conversion_waits_for_the_busy_instance(conversion_time):
    """With one instance, a second conversion waits for the first and then runs on the same instance."""
    conversion_time(0.5)
    unoserver_pool = _started_pool(instance_count=1, wait_seconds=5)
    try:
        outcomes = _convert_at_once(unoserver_pool, [b"PK first", b"PK second"])
    finally:
        unoserver_pool.stop()

    assert outcomes[0] == outcomes[1] and isinstance(outcomes[0], bytes)


def test_a_conversion_still_waiting_when_the_wait_ends_gets_converter_busy(conversion_time):
    """If the only instance stays busy past wait_seconds, the waiting conversion raises ConverterBusyError."""
    conversion_time(2)
    unoserver_pool = _started_pool(instance_count=1, wait_seconds=0.3)
    try:
        first_conversion = threading.Thread(target=unoserver_pool.convert_docx_to_pdf, args=(b"PK first",))
        first_conversion.start()
        while unoserver_pool.instances[0].state is not InstanceState.BUSY:  # the first conversion has the instance
            time.sleep(0.01)
        started = time.monotonic()
        with pytest.raises(ConverterBusyError, match="all 1 unoserver instances stayed busy for 0.3 seconds"):
            unoserver_pool.convert_docx_to_pdf(b"PK second")
        waited_seconds = time.monotonic() - started
        first_conversion.join()
    finally:
        unoserver_pool.stop()

    assert 0.3 <= waited_seconds < 1.5  # the first conversion holds the instance for 2 s


def test_a_conversion_waits_for_an_instance_that_is_starting(monkeypatch):
    """A DOCX sent while LibreOffice starts waits for it instead of failing."""
    monkeypatch.setenv("STAND_IN_UNOSERVER_START_SECONDS", "1")
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(
            instance_count=1, wait_seconds=10, first_port=find_free_port_range(2), unoserver_command=STAND_IN_UNOSERVER
        )
    )
    unoserver_pool.start()
    try:
        pdf_bytes = unoserver_pool.convert_docx_to_pdf(b"PK sent at once")
    finally:
        unoserver_pool.stop()

    assert pdf_bytes.startswith(b"%PDF-")


def test_an_instance_still_starting_when_the_wait_ends_gives_unavailable(monkeypatch):
    """If no instance has answered by the end of the wait, the conversion gets unavailable, not busy."""
    monkeypatch.setenv("STAND_IN_UNOSERVER_START_SECONDS", "5")
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(
            instance_count=1, wait_seconds=0.3, first_port=find_free_port_range(2), unoserver_command=STAND_IN_UNOSERVER
        )
    )
    unoserver_pool.start()
    try:
        with pytest.raises(UnoserverUnavailableError, match="no unoserver instance was ready within 0.3 seconds"):
            unoserver_pool.convert_docx_to_pdf(b"PK too early")
    finally:
        unoserver_pool.stop()


def test_a_document_libreoffice_refuses_leaves_the_instance_idle():
    """A conversion fault fails that DOCX only; the instance is idle again for the next one."""
    unoserver_pool = _started_pool(instance_count=1)
    try:
        with pytest.raises(DocxConversionError):
            unoserver_pool.convert_docx_to_pdf(b"fault: LibreOffice refuses this")
        assert unoserver_pool.instances[0].state is InstanceState.IDLE
        assert unoserver_pool.convert_docx_to_pdf(b"PK next").startswith(b"%PDF-")
    finally:
        unoserver_pool.stop()


def test_after_stop_a_conversion_gets_unavailable():
    """A stopped pool has no instance, so a conversion fails at once."""
    unoserver_pool = _started_pool(instance_count=1)
    unoserver_pool.stop()

    with pytest.raises(UnoserverUnavailableError):
        unoserver_pool.convert_docx_to_pdf(b"PK late")
