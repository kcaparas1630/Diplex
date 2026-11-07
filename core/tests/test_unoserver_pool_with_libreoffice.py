"""Tests the pool with real unoserver and LibreOffice; skipped unless the unoserver command is on PATH (see AGENTS.md)."""

import shutil
import threading
import time
import xmlrpc.client
from pathlib import Path

import pytest

from diplex.engine import InstanceState, UnoserverPool, UnoserverPoolSettings
from localhost_ports import find_free_port_range, wait_until_closed

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


def _process_names_in_group(process_group_id: int) -> list[str]:
    """The command names of every process in the group, from /proc."""
    process_names = []
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            stat_line = stat_path.read_text()
        except OSError:
            continue  # the process ended while we looked
        command_name = stat_line[stat_line.index("(") + 1 : stat_line.rindex(")")]
        fields_after_name = stat_line[stat_line.rindex(")") + 2 :].split()
        if int(fields_after_name[2]) == process_group_id and fields_after_name[0] != "Z":
            process_names.append(command_name)
    return process_names


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
        assert "soffice.bin" in _process_names_in_group(pooled_instance.unoserver_process.process_id)


def test_stopping_the_pool_ends_libreoffice_and_closes_its_ports(running_pool):
    """After stop, no soffice.bin is left running in any instance's group and every port is closed."""
    _wait_until_all_idle(running_pool)
    unoserver_processes = [pooled_instance.unoserver_process for pooled_instance in running_pool.instances]

    running_pool.stop()

    for unoserver_process in unoserver_processes:
        wait_until_closed(unoserver_process.ports.uno_port, timeout_seconds=5)
        wait_until_closed(unoserver_process.ports.xmlrpc_port, timeout_seconds=5)
        assert _process_names_in_group(unoserver_process.process_id) == []


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
