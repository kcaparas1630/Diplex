"""Tests starting and killing one unoserver process, with the stand-in unoserver command and its stand-in LibreOffice."""

import os
import sys
from pathlib import Path

import pytest

from diplex.engine.docx_to_pdf.unoserver_pool.unoserver_process import InstancePorts, start_unoserver_process
from localhost_ports import find_free_port_range, wait_until_closed, wait_until_listening

STAND_IN_UNOSERVER = (sys.executable, str(Path(__file__).with_name("stand_in_unoserver.py")))


@pytest.fixture
def instance_ports() -> InstancePorts:
    """Two free localhost ports for one instance."""
    first_port = find_free_port_range(2)
    return InstancePorts(uno_port=first_port, xmlrpc_port=first_port + 1)


def _start_line(start_log: Path) -> dict[str, str]:
    """The stand-in unoserver's start line, as a dictionary of its key=value fields."""
    (start_line,) = start_log.read_text().splitlines()
    return dict(field.split("=", 1) for field in start_line.split()[1:])


def test_unoserver_starts_on_localhost_ports_with_its_own_profile(tmp_path, monkeypatch, instance_ports):
    """unoserver gets both ports on 127.0.0.1 and a profile and temporary folder inside its scratch folder."""
    start_log = tmp_path / "starts.txt"
    monkeypatch.setenv("STAND_IN_UNOSERVER_LOG", str(start_log))
    scratch_folder = tmp_path / "instance-0"

    unoserver_process = start_unoserver_process(STAND_IN_UNOSERVER, instance_ports, scratch_folder)
    try:
        wait_until_listening(instance_ports.xmlrpc_port, timeout_seconds=10)
        start_fields = _start_line(start_log)
    finally:
        unoserver_process.kill()

    assert start_fields["port"] == str(instance_ports.xmlrpc_port)
    assert start_fields["uno_port"] == str(instance_ports.uno_port)
    assert start_fields["interface"] == start_fields["uno_interface"] == "127.0.0.1"
    assert start_fields["user_installation"] == str(scratch_folder / "profile")
    assert start_fields["temp_dir"] == str(scratch_folder / "temporary")


def test_unoserver_leads_its_own_process_group(tmp_path, monkeypatch, instance_ports):
    """unoserver runs in a new session, so it and the LibreOffice it starts are a process group apart from the engine."""
    start_log = tmp_path / "starts.txt"
    monkeypatch.setenv("STAND_IN_UNOSERVER_LOG", str(start_log))

    unoserver_process = start_unoserver_process(STAND_IN_UNOSERVER, instance_ports, tmp_path / "instance-0")
    try:
        wait_until_listening(instance_ports.xmlrpc_port, timeout_seconds=10)
        process_group_id = int(_start_line(start_log)["pgid"])
    finally:
        unoserver_process.kill()

    assert process_group_id == unoserver_process.process_id != os.getpgid(0)


def test_kill_stops_libreoffice_too_frees_the_ports_and_deletes_the_scratch_folder(tmp_path, instance_ports):
    """Killing the group stops the stand-in LibreOffice, which ignores SIGTERM, so its UNO port closes."""
    scratch_folder = tmp_path / "instance-0"
    unoserver_process = start_unoserver_process(STAND_IN_UNOSERVER, instance_ports, scratch_folder)
    wait_until_listening(instance_ports.uno_port, timeout_seconds=10)
    wait_until_listening(instance_ports.xmlrpc_port, timeout_seconds=10)

    unoserver_process.kill()

    assert unoserver_process.has_exited()
    wait_until_closed(instance_ports.uno_port, timeout_seconds=5)
    wait_until_closed(instance_ports.xmlrpc_port, timeout_seconds=5)
    assert not scratch_folder.exists()


def test_a_start_empties_a_scratch_folder_left_from_before(tmp_path, instance_ports):
    """A profile left in the scratch folder is deleted before unoserver starts, so each start begins clean."""
    scratch_folder = tmp_path / "instance-0"
    (scratch_folder / "profile").mkdir(parents=True)
    (scratch_folder / "profile" / "left-behind.xcu").write_text("from an earlier instance")

    unoserver_process = start_unoserver_process(STAND_IN_UNOSERVER, instance_ports, scratch_folder)
    try:
        assert not (scratch_folder / "profile" / "left-behind.xcu").exists()
        assert (scratch_folder / "temporary").is_dir()
    finally:
        unoserver_process.kill()


def test_a_command_that_does_not_exist_raises_and_leaves_no_scratch_folder(tmp_path, instance_ports):
    """A missing unoserver command raises OSError and cleans up the scratch folder it made."""
    scratch_folder = tmp_path / "instance-0"

    with pytest.raises(OSError):
        start_unoserver_process((str(tmp_path / "no-such-unoserver"),), instance_ports, scratch_folder)

    assert not scratch_folder.exists()
