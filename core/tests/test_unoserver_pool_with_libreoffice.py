"""Tests the pool with real unoserver and LibreOffice; skipped unless the unoserver command is on PATH (see AGENTS.md)."""

import os
import shutil
import signal
import threading
import time
import xmlrpc.client
from pathlib import Path

import pytest

from diplex.engine import InstanceState, UnoserverPool, UnoserverPoolSettings
from diplex.engine.docx_to_pdf.unoserver_client import unoserver_answers
from diplex.engine.docx_to_pdf.unoserver_pool.pooled_instance.unoserver_process import InstancePorts, start_unoserver_process
from localhost_ports import find_free_port_range, wait_until_closed
from process_groups import process_names_in_group

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
LIBREOFFICE_START_SECONDS = 60

pytestmark = pytest.mark.skipif(shutil.which("unoserver") is None, reason="the unoserver command is not on PATH")


def _wait_until_all_idle(unoserver_pool: UnoserverPool) -> None:
    """Wait until every instance has started LibreOffice and is idle, or fail the test."""
    deadline = time.monotonic() + LIBREOFFICE_START_SECONDS
    while any(pooled_instance.state is not InstanceState.IDLE for pooled_instance in unoserver_pool.instances):
        if time.monotonic() > deadline:
            raise AssertionError(f"instances are {[pooled_instance.state for pooled_instance in unoserver_pool.instances]}")
        time.sleep(0.5)


def _wait_until_answering(xmlrpc_port: int) -> None:
    """Wait until the unoserver on the port answers its info call, or fail the test."""
    deadline = time.monotonic() + LIBREOFFICE_START_SECONDS
    while not unoserver_answers(xmlrpc_port, timeout_seconds=5):
        if time.monotonic() > deadline:
            raise AssertionError(f"unoserver on port {xmlrpc_port} did not answer")
        time.sleep(0.5)


@pytest.fixture
def running_pool():
    """A started pool of two real instances on free ports, stopped after the test."""
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(instance_count=2, wait_seconds=LIBREOFFICE_START_SECONDS, first_port=find_free_port_range(4))
    )
    unoserver_pool.start()
    yield unoserver_pool
    unoserver_pool.stop()


def test_each_instance_becomes_idle_with_its_own_libreoffice_in_its_process_group(running_pool):
    """Both instances answer unoserver's info and become idle, each with soffice.bin in its own process group."""
    _wait_until_all_idle(running_pool)

    for pooled_instance in running_pool.instances:
        with xmlrpc.client.ServerProxy(f"http://127.0.0.1:{pooled_instance.ports.xmlrpc_port}") as unoserver:
            assert unoserver.info()["api"] == "3"
        assert "soffice.bin" in process_names_in_group(pooled_instance.unoserver_process.process_id)


def test_stopping_the_pool_ends_libreoffice_and_closes_its_ports(running_pool):
    """After stop, no soffice.bin is left running in any instance's group and every port is closed."""
    _wait_until_all_idle(running_pool)
    unoserver_processes = [pooled_instance.unoserver_process for pooled_instance in running_pool.instances]

    running_pool.stop()

    for unoserver_process in unoserver_processes:
        wait_until_closed(unoserver_process.ports.uno_port, timeout_seconds=5)
        wait_until_closed(unoserver_process.ports.xmlrpc_port, timeout_seconds=5)
        assert process_names_in_group(unoserver_process.process_id) == []


def test_sample_docx_files_convert_side_by_side(running_pool):
    """The first two DOCX files in samples/, sent at once as LibreOffice starts, both come back as PDFs."""
    sample_paths = sorted(SAMPLES_FOLDER.glob("*.docx"))[:2]
    if not sample_paths:
        pytest.skip(f"no DOCX documents in {SAMPLES_FOLDER}")
    pdf_documents = []

    def convert_sample(sample_path: Path) -> None:
        """Convert one sample through the pool and keep its PDF."""
        pdf_documents.append(running_pool.convert_docx_to_pdf(sample_path.read_bytes()))

    threads = [threading.Thread(target=convert_sample, args=(sample_path,)) for sample_path in sample_paths]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(pdf_documents) == len(sample_paths)
    assert all(pdf_bytes.startswith(b"%PDF-") for pdf_bytes in pdf_documents)


def test_killing_an_instance_takes_libreoffice_and_frees_its_ports_for_a_fresh_one(tmp_path):
    """Killing the group ends soffice.bin with unoserver and closes both ports, so a new instance starts on the same ones."""
    first_port = find_free_port_range(2)
    ports = InstancePorts(uno_port=first_port, xmlrpc_port=first_port + 1)
    first_process = start_unoserver_process(("unoserver",), ports, tmp_path / "instance-0")
    try:
        _wait_until_answering(ports.xmlrpc_port)
        assert "soffice.bin" in process_names_in_group(first_process.process_id)
    finally:
        first_process.kill()

    assert process_names_in_group(first_process.process_id) == []
    wait_until_closed(ports.uno_port, timeout_seconds=1)
    wait_until_closed(ports.xmlrpc_port, timeout_seconds=1)
    second_process = start_unoserver_process(("unoserver",), ports, tmp_path / "instance-0")
    try:
        _wait_until_answering(ports.xmlrpc_port)
    finally:
        second_process.kill()


def test_an_instance_whose_unoserver_is_killed_is_restarted_with_a_fresh_libreoffice(running_pool):
    """Killing unoserver alone leaves soffice.bin behind; the keeper kills that group and starts a fresh instance."""
    _wait_until_all_idle(running_pool)
    killed_instance = running_pool.instances[0]
    killed_process = killed_instance.unoserver_process

    os.kill(killed_process.process_id, signal.SIGKILL)
    deadline = time.monotonic() + LIBREOFFICE_START_SECONDS
    while killed_instance.unoserver_process in (None, killed_process) or killed_instance.state is not InstanceState.IDLE:
        assert time.monotonic() < deadline, f"the instance is {killed_instance.state}, not restarted"
        time.sleep(0.5)

    assert process_names_in_group(killed_process.process_id) == []
    assert "soffice.bin" in process_names_in_group(killed_instance.unoserver_process.process_id)
