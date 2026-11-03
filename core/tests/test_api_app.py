"""Tests for the engine's FastAPI app: how it is built, and that uvicorn serves it over real HTTP."""

import json
import socket
import threading
import time
import urllib.request
from importlib.metadata import version

import uvicorn
from fastapi import FastAPI
from uvicorn.importer import import_from_string

from diplex.api import app, create_app

SERVER_START_TIMEOUT_SECONDS = 10


def test_uvicorns_import_string_finds_the_engine_app():
    """`uvicorn diplex.api:app` loads the module-level app."""
    assert import_from_string("diplex.api:app") is app


def test_create_app_names_and_versions_the_engine():
    """The app carries the engine's name and the diplex-core package version into the OpenAPI spec."""
    engine_app = create_app()

    assert isinstance(engine_app, FastAPI)
    assert engine_app.title == "Diplex engine"
    assert engine_app.version == version("diplex-core")


def test_create_app_returns_a_new_app_each_time():
    """Each call builds its own app, so tests never share state through it."""
    assert create_app() is not create_app()


def test_uvicorn_serves_health_over_http():
    """Run by uvicorn on a localhost socket, the app answers GET /health with 200 and status ok."""
    listener = socket.create_server(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config("diplex.api:app", log_level="warning"))
    server_thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    server_thread.start()
    try:
        deadline = time.monotonic() + SERVER_START_TIMEOUT_SECONDS
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started, "uvicorn did not start in time"

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:
            assert response.status == 200
            assert json.load(response) == {"status": "ok"}
    finally:
        server.should_exit = True
        server_thread.join(timeout=SERVER_START_TIMEOUT_SECONDS)
        listener.close()
