"""Samples a Docker container's memory use while the load test runs, through `docker stats`, and keeps the peak."""

from __future__ import annotations

import re
import subprocess
import threading
from collections.abc import Callable

SAMPLE_INTERVAL_SECONDS = 2.0
UNIT_BYTES = {
    "B": 1,
    "kB": 1000,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
}
MEMORY_USAGE_PATTERN = re.compile(r"^\s*([\d.]+)\s*([A-Za-z]+)")


def parse_memory_usage(memory_usage: str) -> int | None:
    """Read the used part of docker stats' MemUsage, like "1.5GiB / 15.6GiB", as bytes; None if it can't."""
    match = MEMORY_USAGE_PATTERN.match(memory_usage)
    if match is None or match.group(2) not in UNIT_BYTES:
        return None
    return round(float(match.group(1)) * UNIT_BYTES[match.group(2)])


def read_container_memory(container_name: str) -> int | None:
    """Ask Docker for the container's memory use now, in bytes; None if Docker can't say."""
    try:
        completed = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container_name],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return parse_memory_usage(completed.stdout)


class PeakMemorySampler:
    """Reads memory use in a background thread every few seconds until stopped, and keeps the highest reading."""

    def __init__(self, read_memory_bytes: Callable[[], int | None], interval_seconds: float = SAMPLE_INTERVAL_SECONDS) -> None:
        """Keep the reader and the interval; sampling starts with start()."""
        self.peak_bytes: int | None = None
        self._read_memory_bytes = read_memory_bytes
        self._interval_seconds = interval_seconds
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._sample_until_stopped, daemon=True)

    def start(self) -> None:
        """Start sampling."""
        self._thread.start()

    def stop(self) -> int | None:
        """Stop sampling and return the peak in bytes, or None if nothing could be read."""
        self._stopped.set()
        self._thread.join()
        return self.peak_bytes

    def _sample_until_stopped(self) -> None:
        """Read the memory use now and then every interval, until stop() is called."""
        while True:
            memory_bytes = self._read_memory_bytes()
            if memory_bytes is not None and (self.peak_bytes is None or memory_bytes > self.peak_bytes):
                self.peak_bytes = memory_bytes
            if self._stopped.wait(self._interval_seconds):
                return
