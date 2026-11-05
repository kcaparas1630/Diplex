"""Tests the engine image's entrypoint with stand-in unoserver and uvicorn commands; it needs Linux (setsid), as in the image."""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[2] / "scripts" / "engine-entrypoint.sh"
STOP_TIMEOUT_SECONDS = 5

# Like unoserver, waits for LibreOffice (a long sleep in its process group) after SIGTERM, so it hangs unless that gets it too.
FAKE_UNOSERVER = """#!/usr/bin/env bash
echo "unoserver $*" >> "$CALLS_FILE"
sleep 300 &
echo $! > "$OFFICE_PID_FILE"
trap 'echo "unoserver got TERM" >> "$CALLS_FILE"; wait; exit 0' TERM
wait
"""
# Like uvicorn, exits on SIGTERM; with API_EXIT_STATUS set it stops on its own after a moment instead.
FAKE_UVICORN = """#!/usr/bin/env bash
echo "uvicorn $*" >> "$CALLS_FILE"
trap 'echo "uvicorn got TERM" >> "$CALLS_FILE"; exit 0' TERM
if [ -n "${API_EXIT_STATUS:-}" ]; then sleep 1; exit "$API_EXIT_STATUS"; fi
sleep 300 &
wait
"""

pytestmark = pytest.mark.skipif(
    shutil.which("setsid") is None or os.name != "posix", reason="the entrypoint runs on Linux, in the engine image"
)


@pytest.fixture
def stand_in_commands(tmp_path) -> dict:
    """Put stand-in unoserver and uvicorn first on PATH, and return the environment and the files they write."""
    commands_folder = tmp_path / "bin"
    commands_folder.mkdir()
    for command_name, script in {"unoserver": FAKE_UNOSERVER, "uvicorn": FAKE_UVICORN}.items():
        command_path = commands_folder / command_name
        command_path.write_text(script)
        command_path.chmod(0o755)
    calls_file, office_pid_file = tmp_path / "calls.txt", tmp_path / "office.pid"
    environment = {
        **os.environ,
        "PATH": f"{commands_folder}:{os.environ['PATH']}",
        "CALLS_FILE": str(calls_file),
        "OFFICE_PID_FILE": str(office_pid_file),
    }
    return {"environment": environment, "calls_file": calls_file, "office_pid_file": office_pid_file}


def _start_entrypoint(environment: dict) -> subprocess.Popen:
    """Run the entrypoint and wait until both stand-ins have started."""
    entrypoint = subprocess.Popen(["bash", str(ENTRYPOINT)], env=environment)
    calls_file = Path(environment["CALLS_FILE"])
    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if calls_file.exists() and len(calls_file.read_text().splitlines()) >= 2:
            return entrypoint
        time.sleep(0.05)
    entrypoint.kill()
    raise AssertionError("the entrypoint did not start both commands")


def _process_is_running(process_id: int) -> bool:
    """Tell whether a process exists and is not a zombie."""
    status_path = Path(f"/proc/{process_id}/status")
    return status_path.exists() and "zombie" not in status_path.read_text()


def test_starts_unoserver_on_localhost_and_the_api_on_port_8000(stand_in_commands):
    """unoserver and LibreOffice listen on localhost only; the API on every interface, port 8000."""
    entrypoint = _start_entrypoint(stand_in_commands["environment"])
    entrypoint.send_signal(signal.SIGTERM)
    entrypoint.wait(timeout=STOP_TIMEOUT_SECONDS)

    calls = stand_in_commands["calls_file"].read_text().splitlines()
    assert "unoserver --interface 127.0.0.1 --uno-interface 127.0.0.1" in calls
    assert "uvicorn diplex.api:app --host 0.0.0.0 --port 8000" in calls


def test_sigterm_stops_both_and_libreoffice(stand_in_commands):
    """docker stop's SIGTERM reaches unoserver, LibreOffice and the API, so the container stops within seconds."""
    entrypoint = _start_entrypoint(stand_in_commands["environment"])
    office_pid = int(stand_in_commands["office_pid_file"].read_text())

    entrypoint.send_signal(signal.SIGTERM)
    entrypoint.wait(timeout=STOP_TIMEOUT_SECONDS)  # hangs if LibreOffice's stand-in doesn't get the signal

    calls = stand_in_commands["calls_file"].read_text().splitlines()
    assert {"unoserver got TERM", "uvicorn got TERM"} <= set(calls)
    assert not _process_is_running(office_pid)


def test_when_the_api_stops_unoserver_is_stopped_and_its_status_kept(stand_in_commands):
    """If one process exits, the other is stopped and the container exits with the first one's status."""
    environment = {**stand_in_commands["environment"], "API_EXIT_STATUS": "3"}
    entrypoint = _start_entrypoint(environment)

    exit_status = entrypoint.wait(timeout=STOP_TIMEOUT_SECONDS + 1)

    assert exit_status == 3
    assert "unoserver got TERM" in stand_in_commands["calls_file"].read_text().splitlines()
