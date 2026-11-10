"""The engine's pool of unoserver instances (ADR 011): it starts them with the engine and hands each conversion an idle one."""

import logging
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ..unoserver_client import UnoserverUnavailableError, convert_docx_to_pdf
from .pooled_instance import InstancePorts, InstanceState, PooledInstance

unoserver_pool_logger = logging.getLogger("diplex.unoserver_pool")
FIRST_UNOSERVER_PORT = 2002  # instance 0 gets unoserver's default ports: 2002 for UNO, 2003 for XML-RPC
DEFAULT_WAIT_SECONDS = 30.0
DEFAULT_READY_TIMEOUT_SECONDS = 60.0  # unoserver sleeps 7 s, then tries LibreOffice for up to about 40 s
# States from which an instance may still become idle, so a conversion is worth waiting for.
STATES_WORTH_WAITING_FOR = frozenset({InstanceState.STARTING, InstanceState.BUSY, InstanceState.RECYCLING})


class ConverterBusyError(Exception):
    """Every unoserver instance stayed busy for the whole wait."""


@dataclass(frozen=True)
class UnoserverPoolSettings:
    """How the pool runs: how many instances, how long a conversion waits for one, and how each one starts."""

    instance_count: int
    wait_seconds: float = DEFAULT_WAIT_SECONDS
    first_port: int = FIRST_UNOSERVER_PORT
    unoserver_command: tuple[str, ...] = ("unoserver",)
    ready_timeout_seconds: float = DEFAULT_READY_TIMEOUT_SECONDS

    def instance_ports(self, instance_index: int) -> InstancePorts:
        """The ports of instance `instance_index`: UNO on first_port + 2i, XML-RPC on the port after it."""
        uno_port = self.first_port + 2 * instance_index
        return InstancePorts(uno_port=uno_port, xmlrpc_port=uno_port + 1)


class UnoserverPool:
    """N unoserver instances on localhost, each converting one document at a time, started and stopped with the engine."""

    def __init__(self, settings: UnoserverPoolSettings) -> None:
        """Hold the settings; nothing starts until start()."""
        self.settings = settings
        self._condition = threading.Condition(threading.RLock())  # shared with every instance's keeper
        self._instances: list[PooledInstance] = []
        self._scratch_root: Path | None = None

    @property
    def instances(self) -> list[PooledInstance]:
        """The pool's instances, in instance order; empty before start() and after stop()."""
        return list(self._instances)

    def start(self) -> None:
        """Start every instance's keeper; each instance takes conversions once LibreOffice answers, a few seconds later."""
        self._scratch_root = Path(tempfile.mkdtemp(prefix="diplex-unoserver-"))
        self._instances = [
            PooledInstance(
                instance_index=instance_index,
                ports=self.settings.instance_ports(instance_index),
                scratch_folder=self._scratch_root / f"instance-{instance_index}",
                unoserver_command=self.settings.unoserver_command,
                ready_timeout_seconds=self.settings.ready_timeout_seconds,
                pool_condition=self._condition,
            )
            for instance_index in range(self.settings.instance_count)
        ]
        for pooled_instance in self._instances:
            pooled_instance.start_keeper()

    def stop(self) -> None:
        """Kill every instance with its LibreOffice and delete the pool's scratch folders."""
        with self._condition:
            stopping_instances, self._instances = self._instances, []  # conversions from now on find no instance
        for pooled_instance in stopping_instances:
            pooled_instance.stop_keeper()
        if self._scratch_root is not None:
            shutil.rmtree(self._scratch_root, ignore_errors=True)
            self._scratch_root = None

    def convert_docx_to_pdf(self, docx_bytes: bytes) -> bytes:
        """Convert a DOCX on an idle instance, which converts nothing else meanwhile."""
        pooled_instance = self._claim_idle_instance()
        try:
            return convert_docx_to_pdf(docx_bytes, port=pooled_instance.ports.xmlrpc_port)
        finally:
            with self._condition:
                pooled_instance.release()

    def _claim_idle_instance(self) -> PooledInstance:
        """Take an idle instance, waiting up to wait_seconds while others are busy or starting."""
        deadline = time.monotonic() + self.settings.wait_seconds
        with self._condition:
            while True:
                for pooled_instance in self._instances:
                    if pooled_instance.claim_if_idle():
                        return pooled_instance
                instance_states = {pooled_instance.state for pooled_instance in self._instances}
                if not instance_states & STATES_WORTH_WAITING_FOR:
                    raise UnoserverUnavailableError("no unoserver instance is running")
                remaining_seconds = deadline - time.monotonic()
                if remaining_seconds <= 0:
                    raise self._wait_ended_error(instance_states)
                self._condition.wait(remaining_seconds)

    def _wait_ended_error(self, instance_states: set[InstanceState]) -> Exception:
        """The error for a conversion that found no idle instance in time: busy if any was converting, else unavailable."""
        wait_seconds = f"{self.settings.wait_seconds:g}"
        if InstanceState.BUSY in instance_states:
            instance_count = len(self._instances)
            return ConverterBusyError(f"all {instance_count} unoserver instances stayed busy for {wait_seconds} seconds")
        return UnoserverUnavailableError(f"no unoserver instance was ready within {wait_seconds} seconds")
