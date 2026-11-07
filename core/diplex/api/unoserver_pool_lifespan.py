"""Runs the app's unoserver pool for as long as the app serves: started before the first request, killed at shutdown."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from diplex.engine import unoserver_pool_logger


@asynccontextmanager
async def run_unoserver_pool(engine_app: FastAPI) -> AsyncIterator[None]:
    """Start engine_app.state.unoserver_pool, serve, then stop it, with its log lines on stderr."""
    _send_pool_logs_to_stderr()
    unoserver_pool = engine_app.state.unoserver_pool
    unoserver_pool.start()
    try:
        yield
    finally:
        unoserver_pool.stop()


def _send_pool_logs_to_stderr() -> None:
    """Print the pool's lines at INFO and above on stderr, like the render job lines, adding the handler only once."""
    if unoserver_pool_logger.handlers:
        return
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    unoserver_pool_logger.addHandler(stderr_handler)
    unoserver_pool_logger.setLevel(logging.INFO)
