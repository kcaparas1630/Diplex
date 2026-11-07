"""Tests the pool with real unoserver and LibreOffice; skipped unless the unoserver command is on PATH (see AGENTS.md)."""

import shutil
import time
import xmlrpc.client
from pathlib import Path

import pytest

from diplex.engine import UnoserverPool, UnoserverPoolSettings
from localhost_ports import find_free_port_range, wait_until_closed

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
LIBREOFFICE_START_SECONDS = 60

pytestmark = pytest.mark.skipif(shutil.which("unoserver") is None, reason="the unoserver command is not on PATH")


def _wait_until_unoserver_answers(xmlrpc_port: int) -> dict:
    """Call unoserver's info until it answers, as it does once LibreOffice is up, and return its answer."""
    deadline = time.monotonic() + LIBREOFFICE_START_SECONDS
    while True:
        try:
            with xmlrpc.client.ServerProxy(f"http://127.0.0.1:{xmlrpc_port}") as unoserver:
                return unoserver.info()
        except (OSError, xmlrpc.client.Error):
            if time.monotonic() > deadline:
                raise
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
    unoserver_pool = UnoserverPool(UnoserverPoolSettings(instance_count=2, first_port=find_free_port_range(4)))
    unoserver_pool.start()
    yield unoserver_pool
    unoserver_pool.stop()


def test_each_instance_runs_its_own_libreoffice_in_its_process_group(running_pool):
    """Both instances answer, each with soffice.bin in its own process group."""
    for unoserver_process in running_pool.running_processes():
        assert _wait_until_unoserver_answers(unoserver_process.ports.xmlrpc_port)["api"] == "3"
        assert "soffice.bin" in _process_names_in_group(unoserver_process.process_id)


def test_stopping_the_pool_ends_libreoffice_and_closes_its_ports(running_pool):
    """After stop, no soffice.bin is left running in any instance's group and every port is closed."""
    running_processes = running_pool.running_processes()
    for unoserver_process in running_processes:
        _wait_until_unoserver_answers(unoserver_process.ports.xmlrpc_port)

    running_pool.stop()

    for unoserver_process in running_processes:
        wait_until_closed(unoserver_process.ports.uno_port, timeout_seconds=5)
        wait_until_closed(unoserver_process.ports.xmlrpc_port, timeout_seconds=5)
        assert _process_names_in_group(unoserver_process.process_id) == []


def test_a_sample_docx_converts_through_the_pool(running_pool):
    """The first DOCX in samples/ comes back as a PDF."""
    sample_paths = sorted(SAMPLES_FOLDER.glob("*.docx"))
    if not sample_paths:
        pytest.skip(f"no DOCX documents in {SAMPLES_FOLDER}")
    for unoserver_process in running_pool.running_processes():
        _wait_until_unoserver_answers(unoserver_process.ports.xmlrpc_port)

    assert running_pool.convert_docx_to_pdf(sample_paths[0].read_bytes()).startswith(b"%PDF-")
