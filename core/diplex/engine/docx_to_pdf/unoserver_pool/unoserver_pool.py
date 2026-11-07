"""The engine's pool of unoserver instances (ADR 011): started with the engine, each on its own ports, killed when it stops."""

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..unoserver_client import UnoserverUnavailableError, convert_docx_to_pdf
from .unoserver_process import InstancePorts, UnoserverProcess, start_unoserver_process

unoserver_pool_logger = logging.getLogger("diplex.unoserver_pool")
FIRST_UNOSERVER_PORT = 2002  # instance 0 gets unoserver's default ports: 2002 for UNO, 2003 for XML-RPC


@dataclass(frozen=True)
class UnoserverPoolSettings:
    """How many unoserver instances the pool runs, from which port, and the command that starts one."""

    instance_count: int
    first_port: int = FIRST_UNOSERVER_PORT
    unoserver_command: tuple[str, ...] = ("unoserver",)

    def instance_ports(self, instance_index: int) -> InstancePorts:
        """The ports of instance `instance_index`: UNO on first_port + 2i, XML-RPC on the port after it."""
        uno_port = self.first_port + 2 * instance_index
        return InstancePorts(uno_port=uno_port, xmlrpc_port=uno_port + 1)


class UnoserverPool:
    """N unoserver instances on localhost, each with its own profile and ports, started and stopped with the engine."""

    def __init__(self, settings: UnoserverPoolSettings) -> None:
        """Hold the settings; nothing starts until start()."""
        self.settings = settings
        self._processes: list[UnoserverProcess] = []
        self._scratch_root: Path | None = None

    def start(self) -> None:
        """Start every instance in a fresh scratch folder; one that can't start is logged and left out."""
        self._scratch_root = Path(tempfile.mkdtemp(prefix="diplex-unoserver-"))
        for instance_index in range(self.settings.instance_count):
            ports = self.settings.instance_ports(instance_index)
            scratch_folder = self._scratch_root / f"instance-{instance_index}"
            try:
                unoserver_process = start_unoserver_process(self.settings.unoserver_command, ports, scratch_folder)
            except OSError as error:
                unoserver_pool_logger.error("unoserver instance %d could not start: %s", instance_index, error)
                continue
            self._processes.append(unoserver_process)
            unoserver_pool_logger.info(
                "unoserver instance %d started: pid=%d uno_port=%d xmlrpc_port=%d",
                instance_index,
                unoserver_process.process_id,
                ports.uno_port,
                ports.xmlrpc_port,
            )

    def stop(self) -> None:
        """Kill every instance with its LibreOffice and delete the pool's scratch folders."""
        for unoserver_process in self._processes:
            unoserver_process.kill()
        self._processes = []
        if self._scratch_root is not None:
            shutil.rmtree(self._scratch_root, ignore_errors=True)
            self._scratch_root = None

    def running_processes(self) -> list[UnoserverProcess]:
        """The instances started and not yet stopped, in instance order."""
        return list(self._processes)

    def convert_docx_to_pdf(self, docx_bytes: bytes) -> bytes:
        """Convert a DOCX on the first instance; spreading conversions over every instance comes with the dispatcher."""
        if not self._processes:
            raise UnoserverUnavailableError("no unoserver instance is running")
        return convert_docx_to_pdf(docx_bytes, port=self._processes[0].ports.xmlrpc_port)
