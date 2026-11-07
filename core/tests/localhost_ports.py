"""Localhost port helpers for the pool tests: find free consecutive ports, and tell or wait until one is listening."""

import random
import socket
import time

PORT_RANGE_START = 20000
PORT_RANGE_END = 60000


def find_free_port_range(port_count: int) -> int:
    """Return the first of port_count consecutive localhost ports that nothing is listening on or bound to."""
    for _ in range(200):
        first_port = random.randrange(PORT_RANGE_START, PORT_RANGE_END - port_count)
        if all(_port_is_free(first_port + offset) for offset in range(port_count)):
            return first_port
    raise RuntimeError(f"found no {port_count} free consecutive ports")


def port_is_listening(port: int) -> bool:
    """Tell whether something accepts connections on the localhost port."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def wait_until_listening(port: int, timeout_seconds: float) -> None:
    """Wait until something accepts connections on the localhost port, or fail the test."""
    deadline = time.monotonic() + timeout_seconds
    while not port_is_listening(port):
        if time.monotonic() > deadline:
            raise AssertionError(f"nothing listened on 127.0.0.1:{port} within {timeout_seconds} s")
        time.sleep(0.05)


def wait_until_closed(port: int, timeout_seconds: float) -> None:
    """Wait until nothing accepts connections on the localhost port, or fail the test."""
    deadline = time.monotonic() + timeout_seconds
    while port_is_listening(port):
        if time.monotonic() > deadline:
            raise AssertionError(f"127.0.0.1:{port} was still listening after {timeout_seconds} s")
        time.sleep(0.05)


def _port_is_free(port: int) -> bool:
    """Tell whether a listener could bind the localhost port now."""
    try:
        with socket.create_server(("127.0.0.1", port)):
            return True
    except OSError:
        return False
