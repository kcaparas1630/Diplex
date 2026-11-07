"""One instance of the unoserver pool: its state, and the keeper thread that starts, supervises, recycles and kills it.

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
EXIT_CHECK_INTERVAL_SECONDS = 0.5  # how often a keeper checks that its idle unoserver is still running
FIRST_RESTART_DELAY_SECONDS = 1.0  # after a failed start; doubles after each further failure
MAX_RESTART_DELAY_SECONDS = 30.0


class InstanceState(Enum):
    """Where an instance is in its life, which says whether the pool may hand it a conversion."""

    STARTING = "starting"  # unoserver started, LibreOffice not answering yet
    IDLE = "idle"  # answering, and free for a conversion
    BUSY = "busy"  # converting one document
    RECYCLING = "recycling"  # being killed, with its whole process group, and started afresh
    DOWN = "down"  # not running: it failed to start, and its keeper will try again
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
        conversions_before_recycle: int,
        pool_condition: threading.Condition,
    ) -> None:
        """Hold what the instance needs to start; nothing runs until start_keeper()."""
        self.instance_index = instance_index
        self.ports = ports
        self._scratch_folder = scratch_folder
        self._unoserver_command = unoserver_command
        self._ready_timeout_seconds = ready_timeout_seconds
        self._conversions_before_recycle = conversions_before_recycle
        self._condition = pool_condition
        self._conversion_count = 0  # successful conversions since this unoserver started
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
        if self._unoserver_process is None or self._unoserver_process.has_exited():
            self._recycle("its unoserver exited")  # caught before a conversion was sent to it
            return False
        self._state = InstanceState.BUSY
        return True

    def release(self, conversion_failure: BaseException | None) -> None:
        """Make a busy instance idle after a conversion that worked, or recycle it after any failure; hold the condition."""
        if self._state is not InstanceState.BUSY:
            return
        if self._unoserver_process is None or self._unoserver_process.has_exited():
            self._recycle("its unoserver exited during a conversion")
        elif conversion_failure is not None:
            # A failed or timed-out LibreOffice may keep failing, or carry what the document did, into the next job.
            self._recycle(f"its conversion failed with {type(conversion_failure).__name__}")
        else:
            self._conversion_count += 1
            if self._conversion_count >= self._conversions_before_recycle:
                self._recycle(f"it converted {self._conversion_count} documents")  # LibreOffice never gives memory back
            else:
                self._set_state(InstanceState.IDLE)

    def _recycle(self, reason: str) -> None:
        """Hand the instance to its keeper to kill and start afresh, before it takes another job; call it holding the condition."""
        self._recycle_reason = reason
        self._set_state(InstanceState.RECYCLING)

    def _keep_running(self) -> None:
        """Keep the instance running until the pool stops: restart it when it exits or fails to start, recycle it when asked."""
        restart_delay_seconds = FIRST_RESTART_DELAY_SECONDS
        while not self._stopping:
            if self._start_and_wait_until_ready():
                restart_delay_seconds = FIRST_RESTART_DELAY_SECONDS
                recycle_reason = self._watch_until_recycled()
                if recycle_reason is None:
                    break
                instance_logger.warning("recycling unoserver instance %d: %s", self.instance_index, recycle_reason)
                self._kill_unoserver()  # the whole process group, so no soffice.bin keeps the UNO port
                continue
            with self._condition:
                if self._condition.wait_for(lambda: self._stopping, timeout=restart_delay_seconds):
                    break
            instance_logger.warning("restarting unoserver instance %d after %g s", self.instance_index, restart_delay_seconds)
            restart_delay_seconds = min(restart_delay_seconds * 2, MAX_RESTART_DELAY_SECONDS)
        self._set_state(InstanceState.STOPPED)
        self._kill_unoserver()

    def _watch_until_recycled(self) -> str | None:
        """Wait while the instance works, recycling it if its unoserver exits while idle; return why, or None on stop."""
        with self._condition:
            while not self._stopping:
                if self._state is InstanceState.RECYCLING:
                    return self._recycle_reason
                if self._state is InstanceState.IDLE and self._unoserver_process.has_exited():
                    self._recycle("its unoserver exited")
                    continue
                self._condition.wait(EXIT_CHECK_INTERVAL_SECONDS)
        return None

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
            self._conversion_count = 0
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
