"""Tests the engine image's entrypoint with a stand-in uvicorn command; it runs on Linux, as in the image."""

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[2] / "scripts" / "engine-entrypoint.sh"
STOP_TIMEOUT_SECONDS = 5

# Like uvicorn, exits on SIGTERM after a moment of shutdown; with API_EXIT_STATUS set it stops on its own instead.
FAKE_UVICORN = """#!/usr/bin/env bash
echo "uvicorn $*" >> "$CALLS_FILE"
trap 'sleep 0.3; echo "uvicorn got TERM" >> "$CALLS_FILE"; exit 0' TERM
if [ -n "${API_EXIT_STATUS:-}" ]; then sleep 0.5; exit "$API_EXIT_STATUS"; fi
sleep 300 &
wait
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="the entrypoint runs on Linux, in the engine image")


@pytest.fixture
def stand_in_uvicorn(tmp_path) -> dict:
    """Put a stand-in uvicorn first on PATH, and return the environment and the file it writes its calls to."""
    commands_folder = tmp_path / "bin"
    commands_folder.mkdir()
    command_path = commands_folder / "uvicorn"
    command_path.write_text(FAKE_UVICORN)
    command_path.chmod(0o755)
    calls_file = tmp_path / "calls.txt"
    environment = {**os.environ, "PATH": f"{commands_folder}:{os.environ['PATH']}", "CALLS_FILE": str(calls_file)}
    return {"environment": environment, "calls_file": calls_file}


def _start_entrypoint(environment: dict) -> subprocess.Popen:
    """Run the entrypoint and wait until the stand-in uvicorn has started."""
    entrypoint = subprocess.Popen(["bash", str(ENTRYPOINT)], env=environment)
    calls_file = Path(environment["CALLS_FILE"])
    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if calls_file.exists() and calls_file.read_text().strip():
            return entrypoint
        time.sleep(0.05)
    entrypoint.kill()
    raise AssertionError("the entrypoint did not start uvicorn")


def test_starts_only_the_api_on_port_8000(stand_in_uvicorn):
    """The entrypoint starts the API on every interface, port 8000; the engine starts unoserver itself."""
    entrypoint = _start_entrypoint(stand_in_uvicorn["environment"])
    entrypoint.send_signal(signal.SIGTERM)
    entrypoint.wait(timeout=STOP_TIMEOUT_SECONDS)

    calls = stand_in_uvicorn["calls_file"].read_text().splitlines()
    assert calls[0] == "uvicorn diplex.api:app --host 0.0.0.0 --port 8000"
    assert not any(call.startswith("unoserver") for call in calls)


def test_sigterm_reaches_the_api_and_waits_for_its_shutdown(stand_in_uvicorn):
    """docker stop's SIGTERM reaches the API, and the container exits only once the API has shut down, with its status."""
    entrypoint = _start_entrypoint(stand_in_uvicorn["environment"])

    entrypoint.send_signal(signal.SIGTERM)
    exit_status = entrypoint.wait(timeout=STOP_TIMEOUT_SECONDS)

    assert exit_status == 0
    assert "uvicorn got TERM" in stand_in_uvicorn["calls_file"].read_text().splitlines()


def test_when_the_api_stops_the_container_exits_with_its_status(stand_in_uvicorn):
    """If the API exits on its own, the entrypoint exits with the API's status."""
    environment = {**stand_in_uvicorn["environment"], "API_EXIT_STATUS": "3"}
    entrypoint = _start_entrypoint(environment)

    exit_status = entrypoint.wait(timeout=STOP_TIMEOUT_SECONDS)

    assert exit_status == 3
