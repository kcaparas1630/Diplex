"""Starts one unoserver in its own session, with its own ports and scratch folder, and kills its whole process group."""

import os
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

LOCALHOST = "127.0.0.1"  # unoserver's ports are unauthenticated, so they never listen beyond the container


@dataclass(frozen=True)
class InstancePorts:
    """The two localhost ports of one unoserver instance: LibreOffice's UNO port and unoserver's XML-RPC port."""

    uno_port: int
    xmlrpc_port: int


class UnoserverProcess:
    """One running unoserver and the LibreOffice it started, which share unoserver's process group."""

    def __init__(self, process: subprocess.Popen, ports: InstancePorts, scratch_folder: Path) -> None:
        """Keep the started process, its ports and the scratch folder it owns."""
        self._process = process
        self.ports = ports
        self.scratch_folder = scratch_folder

    @property
    def process_id(self) -> int:
        """unoserver's process ID, which is also its process group ID."""
        return self._process.pid

    def has_exited(self) -> bool:
        """Tell whether unoserver itself has exited; LibreOffice may still be running in its group."""
        return self._process.poll() is not None

    def kill(self) -> None:
        """Kill unoserver and every LibreOffice process in its group, reap unoserver, and delete its scratch folder."""
        try:
            os.killpg(self._process.pid, signal.SIGKILL)  # signalling unoserver alone leaves soffice.bin running
        except ProcessLookupError:
            pass  # the whole group is already gone
        self._process.wait()
        shutil.rmtree(self.scratch_folder, ignore_errors=True)


def start_unoserver_process(unoserver_command: tuple[str, ...], ports: InstancePorts, scratch_folder: Path) -> UnoserverProcess:
    """Start unoserver in a new session on the ports, with its LibreOffice profile and temporary files in an empty scratch folder."""
    shutil.rmtree(scratch_folder, ignore_errors=True)
    profile_folder = scratch_folder / "profile"
    temporary_folder = scratch_folder / "temporary"  # unoserver writes each input document here while converting it
    temporary_folder.mkdir(parents=True)
    command = [
        *unoserver_command,
        "--interface", LOCALHOST,
        "--uno-interface", LOCALHOST,
        "--port", str(ports.xmlrpc_port),
        "--uno-port", str(ports.uno_port),
        "--user-installation", str(profile_folder),
        "--temp-dir", str(temporary_folder),
    ]
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        shutil.rmtree(scratch_folder, ignore_errors=True)
        raise
    return UnoserverProcess(process, ports, scratch_folder)
