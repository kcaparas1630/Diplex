"""One instance of the unoserver pool: its state, and the keeper thread that starts, recycles and kills it (ADR 011).

The pool and every keeper share one condition: each reads or changes an instance's state only while holding it, and
notifies it after a change, so a conversion waiting for an idle instance wakes up when one becomes free.
"""

import logging
import threading
import time
from enum import Enum
from pathlib import Path

from ...unoserver_client import unoserver_answers
from .unoserver_process import InstancePorts, UnoserverProcess, start_unoserver_process

instance_logger = logging.getLogger("diplex.unoserver_pool")
READY_CHECK_INTERVAL_SECONDS = 0.25
READY_CHECK_TIMEOUT_SECONDS = 5.0  # one info call; LibreOffice answers in milliseconds once up


class InstanceState(Enum):
    """Where an instance is in its life, which says whether the pool may hand it a conversion."""

    STARTING = "starting"  # unoserver started, LibreOffice not answering yet
    IDLE = "idle"  # answering, and free for a conversion
    BUSY = "busy"  # converting one document
    RECYCLING = "recycling"  # being killed, with its whole process group, and started afresh
    DOWN = "down"  # not running: it failed to start, or exited
    STOPPED = "stopped"  # the pool is shutting down


class PooledInstance:
    """One unoserver instance in the pool, kept running by its own keeper thread."""

    def __init__(
        self,
        instance_index: int,
        ports: InstancePorts,
        scratch_folder: Path,
        unoserver_command: tuple[str, ...],
        ready_timeout_seconds: float,
        pool_condition: threading.Condition,
    ) -> None:
        """Hold what the instance needs to start; nothing runs until start_keeper()."""
        self.instance_index = instance_index
        self.ports = ports
        self._scratch_folder = scratch_folder
        self._unoserver_command = unoserver_command
        self._ready_timeout_seconds = ready_timeout_seconds
        self._condition = pool_condition
        self._state = InstanceState.STARTING
        self._stopping = False
        self._recycle_reason = ""
        self._unoserver_process: UnoserverProcess | None = None
        self._keeper_thread = threading.Thread(
            target=self._keep_running, name=f"unoserver-keeper-{instance_index}", daemon=True
        )

    @property
    def state(self) -> InstanceState:
        """The instance's current state; read it while holding the pool's condition."""
        return self._state

    @property
    def unoserver_process(self) -> UnoserverProcess | None:
        """The running unoserver, or None before it starts and after it is killed."""
        return self._unoserver_process

    def start_keeper(self) -> None:
        """Start the keeper thread, which starts unoserver and marks the instance idle once it answers."""
        self._keeper_thread.start()

    def stop_keeper(self) -> None:
        """Ask the keeper to kill the instance, and wait until it has."""
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        self._keeper_thread.join()

    def claim_if_idle(self) -> bool:
        """Mark an idle instance busy and return True, or return False; call it while holding the pool's condition."""
        if self._state is not InstanceState.IDLE:
            return False
        self._state = InstanceState.BUSY
        return True

    def release(self) -> None:
        """Make a busy instance idle again after its conversion, or recycle it if unoserver died; call it holding the condition."""
        if self._state is not InstanceState.BUSY:
            return
        if self._unoserver_process is None or self._unoserver_process.has_exited():
            self._recycle("its unoserver exited during a conversion")
            return
        self._set_state(InstanceState.IDLE)

    def _recycle(self, reason: str) -> None:
        """Hand the instance to its keeper to kill and start afresh, before it takes another job; call it holding the condition."""
        self._recycle_reason = reason
        self._set_state(InstanceState.RECYCLING)

    def _keep_running(self) -> None:
        """Start the instance and keep it, recycling it whenever asked, until the pool stops; then kill it."""
        while True:
            self._start_and_wait_until_ready()
            with self._condition:
                self._condition.wait_for(lambda: self._stopping or self._state is InstanceState.RECYCLING)
                if self._stopping:
                    self._set_state(InstanceState.STOPPED)
                    break
                recycle_reason = self._recycle_reason
            instance_logger.warning("recycling unoserver instance %d: %s", self.instance_index, recycle_reason)
            self._kill_unoserver()  # the whole process group, so no soffice.bin keeps the UNO port
        self._kill_unoserver()

    def _start_and_wait_until_ready(self) -> bool:
        """Start unoserver and mark the instance idle once it answers; mark it down and return False if it never does."""
        started = time.monotonic()
        try:
            unoserver_process = start_unoserver_process(self._unoserver_command, self.ports, self._scratch_folder)
        except OSError as error:
            instance_logger.error("unoserver instance %d could not start: %s", self.instance_index, error)
            self._set_state(InstanceState.DOWN)
            return False
        with self._condition:
            self._unoserver_process = unoserver_process
            self._set_state(InstanceState.STARTING)
        deadline = started + self._ready_timeout_seconds
        while not unoserver_answers(self.ports.xmlrpc_port, READY_CHECK_TIMEOUT_SECONDS):
            failure = self._startup_failure(unoserver_process, deadline)
            if failure:
                instance_logger.error("unoserver instance %d %s", self.instance_index, failure)
                self._kill_unoserver()
                self._set_state(InstanceState.DOWN)
                return False
            with self._condition:
                if self._condition.wait_for(lambda: self._stopping, timeout=READY_CHECK_INTERVAL_SECONDS):
                    return False
        self._set_state(InstanceState.IDLE)
        instance_logger.info(
            "unoserver instance %d ready in %.1f s: pid=%d uno_port=%d xmlrpc_port=%d",
            self.instance_index,
            time.monotonic() - started,
            unoserver_process.process_id,
            self.ports.uno_port,
            self.ports.xmlrpc_port,
        )
        return True

    def _startup_failure(self, unoserver_process: UnoserverProcess, deadline: float) -> str | None:
        """Say why a starting instance will never answer, or return None while it still might."""
        if unoserver_process.has_exited():
            return "exited before answering"
        if time.monotonic() > deadline:
            return f"did not answer within {self._ready_timeout_seconds:g} seconds"
        return None

    def _kill_unoserver(self) -> None:
        """Kill the instance's process group, if it has one, and forget it."""
        with self._condition:
            unoserver_process, self._unoserver_process = self._unoserver_process, None
        if unoserver_process is not None:
            unoserver_process.kill()

    def _set_state(self, new_state: InstanceState) -> None:
        """Change the state and wake whoever waits on the pool's condition; never leaves STOPPED."""
        with self._condition:
            if self._state is InstanceState.STOPPED:
                return
            self._state = new_state
            self._condition.notify_all()
