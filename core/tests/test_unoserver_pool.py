"""Tests the unoserver pool with the stand-in unoserver command: N instances, each on its own ports and profile."""

import logging
import sys
from pathlib import Path

import pytest

from diplex.engine import UnoserverPool, UnoserverPoolSettings, UnoserverUnavailableError
from localhost_ports import find_free_port_range, wait_until_closed, wait_until_listening

STAND_IN_UNOSERVER = (sys.executable, str(Path(__file__).with_name("stand_in_unoserver.py")))


def _pool_settings(instance_count: int) -> UnoserverPoolSettings:
    """Settings for a pool of stand-in instances on free localhost ports."""
    return UnoserverPoolSettings(
        instance_count=instance_count,
        first_port=find_free_port_range(2 * instance_count),
        unoserver_command=STAND_IN_UNOSERVER,
    )


def _start_lines(start_log: Path) -> list[dict[str, str]]:
    """Each stand-in unoserver start line, as a dictionary of its key=value fields."""
    return [dict(field.split("=", 1) for field in line.split()[1:]) for line in start_log.read_text().splitlines()]


@pytest.fixture
def start_log(tmp_path, monkeypatch) -> Path:
    """The file every stand-in unoserver started during the test writes its start line to."""
    log_path = tmp_path / "starts.txt"
    monkeypatch.setenv("STAND_IN_UNOSERVER_LOG", str(log_path))
    return log_path


def test_instance_ports_follow_unoservers_defaults_two_by_two():
    """Instance 0 gets unoserver's defaults, 2002 (UNO) and 2003 (XML-RPC); each next instance the next two ports."""
    settings = UnoserverPoolSettings(instance_count=3)

    assert [(ports.uno_port, ports.xmlrpc_port) for ports in map(settings.instance_ports, range(3))] == [
        (2002, 2003),
        (2004, 2005),
        (2006, 2007),
    ]


def test_start_runs_n_instances_each_with_its_own_ports_profile_and_process_group(start_log):
    """Three instances: six distinct localhost ports, three profile folders, three process groups."""
    unoserver_pool = UnoserverPool(_pool_settings(instance_count=3))
    unoserver_pool.start()
    try:
        running_processes = unoserver_pool.running_processes()
        for unoserver_process in running_processes:
            wait_until_listening(unoserver_process.ports.xmlrpc_port, timeout_seconds=10)
        start_lines = _start_lines(start_log)
    finally:
        unoserver_pool.stop()

    assert len(running_processes) == len(start_lines) == 3
    all_ports = [int(line[port_name]) for line in start_lines for port_name in ("port", "uno_port")]
    assert len(set(all_ports)) == 6
    assert len({line["user_installation"] for line in start_lines}) == 3
    assert len({line["pgid"] for line in start_lines}) == 3
    assert {line["interface"] for line in start_lines} == {line["uno_interface"] for line in start_lines} == {"127.0.0.1"}


def test_stop_kills_every_instance_with_its_libreoffice_and_deletes_the_scratch_folders(start_log):
    """After stop, no instance's UNO or XML-RPC port is listening and no profile is left on disk."""
    unoserver_pool = UnoserverPool(_pool_settings(instance_count=2))
    unoserver_pool.start()
    running_processes = unoserver_pool.running_processes()
    for unoserver_process in running_processes:
        wait_until_listening(unoserver_process.ports.uno_port, timeout_seconds=10)
        wait_until_listening(unoserver_process.ports.xmlrpc_port, timeout_seconds=10)

    unoserver_pool.stop()

    for unoserver_process in running_processes:
        wait_until_closed(unoserver_process.ports.uno_port, timeout_seconds=5)
        wait_until_closed(unoserver_process.ports.xmlrpc_port, timeout_seconds=5)
        assert not unoserver_process.scratch_folder.exists()
    assert unoserver_pool.running_processes() == []


def test_a_conversion_goes_to_the_first_instance(start_log):
    """Until the dispatcher, every conversion is sent to instance 0."""
    unoserver_pool = UnoserverPool(_pool_settings(instance_count=2))
    unoserver_pool.start()
    try:
        first_process = unoserver_pool.running_processes()[0]
        wait_until_listening(first_process.ports.xmlrpc_port, timeout_seconds=10)

        pdf_bytes = unoserver_pool.convert_docx_to_pdf(b"PK stand-in DOCX")
    finally:
        unoserver_pool.stop()

    assert pdf_bytes == f"%PDF-1.7 converted by {first_process.process_id}".encode()


def test_an_instance_that_cannot_start_is_logged_and_conversions_get_unavailable(tmp_path, caplog):
    """With no unoserver command, the engine still starts: the failure is logged and a DOCX gets UnoserverUnavailableError."""
    settings = UnoserverPoolSettings(instance_count=1, unoserver_command=(str(tmp_path / "no-such-unoserver"),))
    unoserver_pool = UnoserverPool(settings)
    caplog.set_level(logging.INFO, logger="diplex.unoserver_pool")

    unoserver_pool.start()
    try:
        with pytest.raises(UnoserverUnavailableError):
            unoserver_pool.convert_docx_to_pdf(b"PK stand-in DOCX")
    finally:
        unoserver_pool.stop()

    assert "unoserver instance 0 could not start" in caplog.text
