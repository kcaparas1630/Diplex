"""Tests recycling pool instances with the stand-in unoserver: the whole process group goes, and a fresh instance comes."""

import logging
import sys
import time
from pathlib import Path

import pytest

from diplex.engine import InstanceState, UnoserverPool, UnoserverPoolSettings, UnoserverUnavailableError
from localhost_ports import find_free_port_range
from process_groups import process_names_in_group

STAND_IN_UNOSERVER = (sys.executable, str(Path(__file__).with_name("stand_in_unoserver.py")))
INSTANCE_START_SECONDS = 10


def _wait_until_idle(unoserver_pool: UnoserverPool) -> None:
    """Wait until the pool's only instance is idle, or fail the test."""
    deadline = time.monotonic() + INSTANCE_START_SECONDS
    while unoserver_pool.instances[0].state is not InstanceState.IDLE:
        if time.monotonic() > deadline:
            raise AssertionError(f"the instance is {unoserver_pool.instances[0].state}, not idle")
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


@pytest.fixture
def one_instance_pool(start_log):
    """A started pool of one stand-in instance, idle, stopped after the test."""
    unoserver_pool = UnoserverPool(
        UnoserverPoolSettings(instance_count=1, first_port=find_free_port_range(2), unoserver_command=STAND_IN_UNOSERVER)
    )
    unoserver_pool.start()
    _wait_until_idle(unoserver_pool)
    yield unoserver_pool
    unoserver_pool.stop()


def test_recycling_kills_the_libreoffice_that_outlived_unoserver_and_restarts_on_its_ports(one_instance_pool, start_log, caplog):
    """unoserver dies mid-conversion, leaving its LibreOffice on the UNO port; recycling kills that group and starts afresh."""
    caplog.set_level(logging.INFO, logger="diplex.unoserver_pool")
    first_start = _start_lines(start_log)[0]
    first_group_id = int(first_start["pgid"])

    with pytest.raises(UnoserverUnavailableError):
        one_instance_pool.convert_docx_to_pdf(b"crash the stand-in unoserver")
    _wait_until_idle(one_instance_pool)  # the new LibreOffice could bind the UNO port, so the old one let it go

    second_start = _start_lines(start_log)[1]
    assert process_names_in_group(first_group_id) == []
    assert (second_start["port"], second_start["uno_port"]) == (first_start["port"], first_start["uno_port"])
    assert second_start["pid"] != first_start["pid"]
    assert one_instance_pool.convert_docx_to_pdf(b"PK next") == f"%PDF-1.7 converted by {second_start['pid']}".encode()
    assert "recycling unoserver instance 0: its unoserver exited during a conversion" in caplog.text


def test_a_conversion_waits_for_a_recycling_instance(one_instance_pool, monkeypatch):
    """A conversion sent while the only instance is recycling waits for the fresh instance instead of failing."""
    monkeypatch.setenv("STAND_IN_UNOSERVER_START_SECONDS", "0.5")
    with pytest.raises(UnoserverUnavailableError):
        one_instance_pool.convert_docx_to_pdf(b"crash the stand-in unoserver")

    assert one_instance_pool.instances[0].state in {InstanceState.RECYCLING, InstanceState.STARTING}
    assert one_instance_pool.convert_docx_to_pdf(b"PK sent during the recycle").startswith(b"%PDF-")


def test_a_recycle_deletes_the_old_profile(one_instance_pool):
    """The fresh instance starts with an empty scratch folder: nothing the last document did to the profile is kept."""
    profile_folder = one_instance_pool.instances[0].unoserver_process.scratch_folder / "profile"
    profile_folder.mkdir(parents=True, exist_ok=True)
    (profile_folder / "left-by-a-document.xcu").write_text("changed settings")

    with pytest.raises(UnoserverUnavailableError):
        one_instance_pool.convert_docx_to_pdf(b"crash the stand-in unoserver")
    _wait_until_idle(one_instance_pool)

    assert not (profile_folder / "left-by-a-document.xcu").exists()
