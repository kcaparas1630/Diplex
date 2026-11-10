"""Unit tests for GET /health."""

import io
import threading
import time
import zipfile

import anyio
import pytest
from fastapi.testclient import TestClient

from diplex.api import create_app
from diplex.definition import API_VERSION_HEADER, CURRENT_API_VERSION
from diplex.engine import UnoserverUnavailableError
from stand_in_unoserver_pool import StandInUnoserverPool


@pytest.fixture
def engine_client() -> TestClient:
    """A test client for a new engine app."""
    return TestClient(create_app())


def test_health_answers_200_with_status_ok(engine_client):
    """GET /health returns 200 and {"status": "ok"}."""
    response = engine_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_only_answers_get(engine_client):
    """Other methods get 405."""
    assert engine_client.post("/health").status_code == 405


def test_the_openapi_spec_describes_health_with_its_contract_model(engine_client):
    """The OpenAPI spec documents GET /health with HealthStatus."""
    spec = engine_client.get("/openapi.json").json()

    success = spec["paths"]["/health"]["get"]["responses"]["200"]
    assert success["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/HealthStatus"}
    assert spec["components"]["schemas"]["HealthStatus"]["properties"]["status"]["const"] == "ok"


def test_health_answers_while_every_request_thread_is_busy():
    """With the thread pool cut to one thread and a DOCX holding it, /health still answers at once."""
    conversion_started, release_conversion = threading.Event(), threading.Event()

    def held_conversion(docx_bytes):
        """Hold the only request thread until the test releases it."""
        conversion_started.set()
        release_conversion.wait(10)
        raise UnoserverUnavailableError("released by the test")

    with TestClient(create_app(unoserver_pool=StandInUnoserverPool(held_conversion))) as client:
        client.portal.call(_limit_request_threads_to_one)
        render_thread = threading.Thread(
            target=client.post,
            args=("/render",),
            kwargs={"files": {"document": ("held.docx", _word_package())}, "headers": {API_VERSION_HEADER: CURRENT_API_VERSION}},
        )
        render_thread.start()
        assert conversion_started.wait(10)
        try:
            started = time.monotonic()
            health_response = client.get("/health")
            answered_after = time.monotonic() - started
        finally:
            release_conversion.set()
            render_thread.join(10)

    assert health_response.status_code == 200
    assert answered_after < 1


async def _limit_request_threads_to_one() -> None:
    """Shrink AnyIO's default thread limiter, which FastAPI runs plain routes on, to one thread."""
    anyio.to_thread.current_default_thread_limiter().total_tokens = 1


def _word_package() -> bytes:
    """A zip that the type check takes for a DOCX: just a [Content_Types].xml naming a Word document part."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as package:
        package.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
    return zip_buffer.getvalue()
