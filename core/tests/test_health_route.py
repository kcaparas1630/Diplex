"""Unit tests for GET /health."""

import pytest
from fastapi.testclient import TestClient

from diplex.api import create_app


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
