"""Tests for the engine's FastAPI app."""

import json
import socket
import threading
import time
import urllib.request
from importlib.metadata import version

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from uvicorn.importer import import_from_string

from diplex.api import app, create_app
from diplex.api.upload_limit_setting import MAX_UPLOAD_BYTES_VARIABLE
from stand_in_unoserver_pool import StandInUnoserverPool

SERVER_START_TIMEOUT_SECONDS = 10


def test_uvicorns_import_string_finds_the_engine_app():
    """`uvicorn diplex.api:app` loads the module-level app."""
    assert import_from_string("diplex.api:app") is app


def test_create_app_names_and_versions_the_engine():
    """The app has the engine's name and package version."""
    engine_app = create_app()

    assert isinstance(engine_app, FastAPI)
    assert engine_app.title == "Diplex engine"
    assert engine_app.version == version("diplex-core")


def test_create_app_returns_a_new_app_each_time():
    """Each call builds a new app."""
    assert create_app() is not create_app()


def test_create_app_limits_uploads_to_the_configured_size(monkeypatch):
    """The app answers 413 to a body over DIPLEX_MAX_UPLOAD_BYTES, on any route, before routing."""
    monkeypatch.setenv(MAX_UPLOAD_BYTES_VARIABLE, "10")

    with TestClient(create_app(unoserver_pool=StandInUnoserverPool())) as client:
        over_limit_response = client.post("/health", content=b"x" * 11)
        within_limit_response = client.post("/health", content=b"x" * 10)

    assert over_limit_response.status_code == 413
    assert within_limit_response.status_code == 405  # /health is GET only, so the body got past the limit


def test_create_app_refuses_an_unreadable_limit(monkeypatch):
    """An engine started with a limit it can't read fails at once, instead of running unlimited."""
    monkeypatch.setenv(MAX_UPLOAD_BYTES_VARIABLE, "50MB")

    with pytest.raises(ValueError, match=MAX_UPLOAD_BYTES_VARIABLE):
        create_app()


def test_uvicorn_serves_health_over_http():
    """uvicorn serves GET /health over real HTTP (without the lifespan, so no unoserver starts)."""
    listener = socket.create_server(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config("diplex.api:app", log_level="warning", lifespan="off"))
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
