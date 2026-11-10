"""Tests the unoserver pool's instances with the stand-in unoserver command: starting, readiness, failures and stopping."""

import logging
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

from diplex.engine import InstanceState, UnoserverPool, UnoserverPoolSettings, UnoserverUnavailableError
from localhost_ports import find_free_port_range, wait_until_closed

STAND_IN_UNOSERVER = (sys.executable, str(Path(__file__).with_name("stand_in_unoserver.py")))
INSTANCE_START_SECONDS = 10


def _pool_settings(instance_count: int, **other_settings) -> UnoserverPoolSettings:
    """Settings for a pool of stand-in instances on free localhost ports."""
    return UnoserverPoolSettings(
        instance_count=instance_count,
        first_port=find_free_port_range(2 * instance_count),
        unoserver_command=STAND_IN_UNOSERVER,
        **other_settings,
    )


def _wait_until_all_are(unoserver_pool: UnoserverPool, expected_state: InstanceState) -> None:
    """Wait until every instance of the pool is in the expected state, or fail the test."""
    deadline = time.monotonic() + INSTANCE_START_SECONDS
    while any(pooled_instance.state is not expected_state for pooled_instance in unoserver_pool.instances):
        if time.monotonic() > deadline:
            states = [pooled_instance.state for pooled_instance in unoserver_pool.instances]
            raise AssertionError(f"instances are {states}, not all {expected_state}")
        time.sleep(0.02)


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
    """Three instances become idle: six distinct localhost ports, three profile folders, three process groups."""
    unoserver_pool = UnoserverPool(_pool_settings(instance_count=3))
    unoserver_pool.start()
    try:
        _wait_until_all_are(unoserver_pool, InstanceState.IDLE)
        start_lines = _start_lines(start_log)
    finally:
        unoserver_pool.stop()

    assert len(start_lines) == 3
    all_ports = [int(line[port_name]) for line in start_lines for port_name in ("port", "uno_port")]
    assert len(set(all_ports)) == 6
    assert len({line["user_installation"] for line in start_lines}) == 3
    assert len({line["pgid"] for line in start_lines}) == 3
    assert {line["interface"] for line in start_lines} == {line["uno_interface"] for line in start_lines} == {"127.0.0.1"}


def test_an_instance_takes_conversions_only_once_it_answers(monkeypatch):
    """While unoserver is still starting LibreOffice the instance is starting, and idle once unoserver answers."""
    monkeypatch.setenv("STAND_IN_UNOSERVER_START_SECONDS", "1")
    unoserver_pool = UnoserverPool(_pool_settings(instance_count=1))
    unoserver_pool.start()
    try:
        assert unoserver_pool.instances[0].state is InstanceState.STARTING
        _wait_until_all_are(unoserver_pool, InstanceState.IDLE)
    finally:
        unoserver_pool.stop()


def test_stop_kills_every_instance_with_its_libreoffice_and_deletes_the_scratch_folders(start_log):
    """After stop, no instance's UNO or XML-RPC port is listening and no profile is left on disk."""
    unoserver_pool = UnoserverPool(_pool_settings(instance_count=2))
    unoserver_pool.start()
    _wait_until_all_are(unoserver_pool, InstanceState.IDLE)
    unoserver_processes = [pooled_instance.unoserver_process for pooled_instance in unoserver_pool.instances]

    unoserver_pool.stop()

    for unoserver_process in unoserver_processes:
        wait_until_closed(unoserver_process.ports.uno_port, timeout_seconds=5)
        wait_until_closed(unoserver_process.ports.xmlrpc_port, timeout_seconds=5)
        assert not unoserver_process.scratch_folder.exists()
    assert unoserver_pool.instances == []


def test_an_instance_that_cannot_start_is_down_and_a_docx_gets_unavailable_at_once(tmp_path, caplog):
    """With no unoserver command, the failure is logged and a conversion fails at once instead of waiting."""
    settings = UnoserverPoolSettings(instance_count=1, unoserver_command=(str(tmp_path / "no-such-unoserver"),))
    unoserver_pool = UnoserverPool(settings)
    caplog.set_level(logging.INFO, logger="diplex.unoserver_pool")
    unoserver_pool.start()
    try:
        _wait_until_all_are(unoserver_pool, InstanceState.DOWN)
        started = time.monotonic()
        with pytest.raises(UnoserverUnavailableError, match="no unoserver instance is running"):
            unoserver_pool.convert_docx_to_pdf(b"PK stand-in DOCX")
        assert time.monotonic() - started < 1
    finally:
        unoserver_pool.stop()

    assert "unoserver instance 0 could not start" in caplog.text


def test_an_instance_that_exits_before_answering_is_down(caplog):
    """A unoserver that exits while starting (here, Python running nothing) is logged and marked down."""
    unoserver_pool = UnoserverPool(replace(_pool_settings(instance_count=1), unoserver_command=(sys.executable, "-c", "pass")))
    caplog.set_level(logging.INFO, logger="diplex.unoserver_pool")
    unoserver_pool.start()
    try:
        _wait_until_all_are(unoserver_pool, InstanceState.DOWN)
    finally:
        unoserver_pool.stop()

    assert "unoserver instance 0 exited before answering" in caplog.text


def test_an_instance_that_never_answers_is_killed_and_down(monkeypatch, caplog):
    """An instance still silent at ready_timeout_seconds is killed with its LibreOffice and marked down."""
    monkeypatch.setenv("STAND_IN_UNOSERVER_START_SECONDS", "30")
    unoserver_pool = UnoserverPool(_pool_settings(instance_count=1, ready_timeout_seconds=0.5))
    caplog.set_level(logging.INFO, logger="diplex.unoserver_pool")
    unoserver_pool.start()
    try:
        _wait_until_all_are(unoserver_pool, InstanceState.DOWN)
        assert unoserver_pool.instances[0].unoserver_process is None
        wait_until_closed(unoserver_pool.settings.instance_ports(0).uno_port, timeout_seconds=5)
    finally:
        unoserver_pool.stop()

    assert "unoserver instance 0 did not answer within 0.5 seconds" in caplog.text
