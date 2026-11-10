"""Tests the keepers' supervision with the stand-in unoserver: an instance that exits is restarted and rejoins the pool."""

import logging
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from diplex.engine import InstanceState, UnoserverPool, UnoserverPoolSettings
from localhost_ports import find_free_port_range
from process_groups import process_names_in_group

STAND_IN_UNOSERVER = (sys.executable, str(Path(__file__).with_name("stand_in_unoserver.py")))
INSTANCE_START_SECONDS = 10


def _wait_until(unoserver_pool: UnoserverPool, expected_state: InstanceState, timeout_seconds: float = INSTANCE_START_SECONDS) -> None:
    """Wait until the pool's only instance is in the expected state, or fail the test."""
    deadline = time.monotonic() + timeout_seconds
    while unoserver_pool.instances[0].state is not expected_state:
        if time.monotonic() > deadline:
            raise AssertionError(f"the instance is {unoserver_pool.instances[0].state}, not {expected_state}")
        time.sleep(0.02)


def _start_lines(start_log: Path) -> list[dict[str, str]]:
    """Each stand-in unoserver start line, as a dictionary of its key=value fields."""
    if not start_log.exists():
        return []
    return [dict(field.split("=", 1) for field in line.split()[1:]) for line in start_log.read_text().splitlines()]


def _wait_until_exited(process_id: int) -> None:
    """Wait until the process has exited (it is a zombie or gone), so the engine's poll sees it."""
    status_path = Path(f"/proc/{process_id}/status")
    deadline = time.monotonic() + 5
    while status_path.exists() and "zombie" not in status_path.read_text():
        assert time.monotonic() < deadline, f"process {process_id} did not exit"
        time.sleep(0.01)


@pytest.fixture
def start_log(tmp_path, monkeypatch) -> Path:
    """The file every stand-in unoserver started during the test writes its start line to."""
    log_path = tmp_path / "starts.txt"
    monkeypatch.setenv("STAND_IN_UNOSERVER_LOG", str(log_path))
    return log_path


@pytest.fixture
def one_instance_pool(start_log):
    """A started pool of one stand-in instance, stopped after the test."""
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(instance_count=1, first_port=find_free_port_range(2), unoserver_command=STAND_IN_UNOSERVER)
    )
    unoserver_pool.start()
    yield unoserver_pool
    unoserver_pool.stop()


@pytest.mark.parametrize("kill_whole_group", [False, True], ids=["unoserver-only", "whole-group"])
def test_an_idle_instance_that_exits_is_restarted_and_rejoins_the_pool(one_instance_pool, start_log, caplog, kill_whole_group):
    """Killing an idle instance (unoserver alone, or with its LibreOffice) gets it restarted on its ports, converting again."""
    caplog.set_level(logging.INFO, logger="diplex.unoserver_pool")
    _wait_until(one_instance_pool, InstanceState.IDLE)
    first_start = _start_lines(start_log)[0]

    if kill_whole_group:
        os.killpg(int(first_start["pgid"]), signal.SIGKILL)
    else:
        os.kill(int(first_start["pid"]), signal.SIGKILL)  # its LibreOffice stays, holding the UNO port
    deadline = time.monotonic() + INSTANCE_START_SECONDS
    while len(_start_lines(start_log)) < 2:
        assert time.monotonic() < deadline, "the killed instance was not restarted"
        time.sleep(0.02)
    _wait_until(one_instance_pool, InstanceState.IDLE)

    second_start = _start_lines(start_log)[1]
    assert (second_start["port"], second_start["uno_port"]) == (first_start["port"], first_start["uno_port"])
    assert process_names_in_group(int(first_start["pgid"])) == []
    assert one_instance_pool.convert_docx_to_pdf(b"PK after the restart") == f"%PDF-1.7 converted by {second_start['pid']}".encode()
    assert "recycling unoserver instance 0: its unoserver exited" in caplog.text


def test_a_conversion_never_goes_to_an_idle_instance_that_has_exited(one_instance_pool, start_log):
    """A DOCX sent right after the idle unoserver died waits for its restart instead of failing."""
    _wait_until(one_instance_pool, InstanceState.IDLE)
    first_process_id = int(_start_lines(start_log)[0]["pid"])
    os.kill(first_process_id, signal.SIGKILL)
    _wait_until_exited(first_process_id)

    pdf_bytes = one_instance_pool.convert_docx_to_pdf(b"PK sent at once")

    assert pdf_bytes == f"%PDF-1.7 converted by {_start_lines(start_log)[1]['pid']}".encode()


def test_a_failed_start_is_retried_after_a_delay_that_doubles(tmp_path, monkeypatch, start_log, caplog):
    """While unoserver can't start, the keeper tries again 1 s and then 2 s later; stopping doesn't wait out the delay."""
    caplog.set_level(logging.INFO, logger="diplex.unoserver_pool")
    fail_marker = tmp_path / "fail"
    fail_marker.touch()
    monkeypatch.setenv("STAND_IN_UNOSERVER_FAIL_WHILE", str(fail_marker))
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(instance_count=1, first_port=find_free_port_range(2), unoserver_command=STAND_IN_UNOSERVER)
    )
    unoserver_pool.start()
    try:
        deadline = time.monotonic() + INSTANCE_START_SECONDS
        while len(_start_lines(start_log)) < 3:
            assert time.monotonic() < deadline, "the keeper did not retry three times"
            time.sleep(0.02)
        attempt_times = [float(line["at"]) for line in _start_lines(start_log)]
    finally:
        stop_started = time.monotonic()
        unoserver_pool.stop()
        stop_seconds = time.monotonic() - stop_started

    first_delay, second_delay = attempt_times[1] - attempt_times[0], attempt_times[2] - attempt_times[1]
    assert 1 <= first_delay < 2.5  # 1 s, plus noticing the exit and starting Python
    assert 2 <= second_delay < 3.5
    assert second_delay - first_delay > 0.5  # the delay grew
    assert stop_seconds < 1  # the 4 s delay before the next attempt is cut short
    assert "restarting unoserver instance 0 after 1 s" in caplog.text
    assert "restarting unoserver instance 0 after 2 s" in caplog.text


def test_an_instance_that_could_not_start_rejoins_once_it_can(tmp_path, monkeypatch, start_log):
    """When the cause goes away, the next attempt succeeds and the instance converts."""
    fail_marker = tmp_path / "fail"
    fail_marker.touch()
    monkeypatch.setenv("STAND_IN_UNOSERVER_FAIL_WHILE", str(fail_marker))
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(instance_count=1, first_port=find_free_port_range(2), unoserver_command=STAND_IN_UNOSERVER)
    )
    unoserver_pool.start()
    try:
        _wait_until(unoserver_pool, InstanceState.DOWN)
        fail_marker.unlink()
        _wait_until(unoserver_pool, InstanceState.IDLE)

        assert unoserver_pool.convert_docx_to_pdf(b"PK after recovering").startswith(b"%PDF-")
    finally:
        unoserver_pool.stop()
