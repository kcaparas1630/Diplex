"""Tests the Diplex-Api-Version header on /render: required, checked against the versions the engine serves."""

import pytest
from fastapi.testclient import TestClient

from diplex.api import create_app
from diplex.api.api_key import API_KEY_VARIABLE
from diplex.definition import API_VERSION_HEADER, CURRENT_API_VERSION, SUPPORTED_API_VERSIONS, RenderErrorCode
from stand_in_unoserver_pool import StandInUnoserverPool

NOT_A_DOCUMENT = b"plain text, not a document"


def _post_render(headers: dict[str, str]):
    """Send a non-document to /render with the given headers; a request that gets past the checks gets 415."""
    with TestClient(create_app(unoserver_pool=StandInUnoserverPool())) as client:
        return client.post("/render", files={"document": ("upload.txt", NOT_A_DOCUMENT)}, headers=headers)


def test_the_current_version_is_1_and_served():
    """Version 1 is the current API version, and the engine serves it."""
    assert CURRENT_API_VERSION == "1" and CURRENT_API_VERSION in SUPPORTED_API_VERSIONS


def test_a_request_with_a_supported_version_gets_through():
    """Diplex-Api-Version: 1 gets past the check (here to the 415 for a text file)."""
    assert _post_render({API_VERSION_HEADER: "1"}).status_code == 415


@pytest.mark.parametrize("headers", [{}, {API_VERSION_HEADER: "2"}, {API_VERSION_HEADER: "v1"}, {API_VERSION_HEADER: ""}])
def test_a_missing_or_unknown_version_gets_400(headers):
    """No header, or a version the engine doesn't serve, gets 400 unsupported_api_version naming what to send."""
    response = _post_render(headers)

    assert response.status_code == 400
    assert response.json() == {
        "code": RenderErrorCode.UNSUPPORTED_API_VERSION,
        "message": "send the Diplex-Api-Version header with one of: 1",
    }


def test_the_key_is_checked_before_the_version(monkeypatch):
    """With a key set, a request with neither gets 401, so an unauthenticated caller learns nothing about versions."""
    monkeypatch.setenv(API_KEY_VARIABLE, "test-key-0123456789abcdef")

    assert _post_render({}).status_code == 401


def test_health_needs_no_version():
    """GET /health answers without the header."""
    with TestClient(create_app(unoserver_pool=StandInUnoserverPool())) as client:
        assert client.get("/health").status_code == 200


def test_the_spec_lists_the_header_as_required_with_the_served_versions():
    """/render's OpenAPI operation has a required Diplex-Api-Version header limited to the served versions."""
    openapi_spec = create_app(unoserver_pool=StandInUnoserverPool()).openapi()

    (parameter,) = openapi_spec["paths"]["/render"]["post"]["parameters"]
    assert (parameter["name"], parameter["in"], parameter["required"]) == (API_VERSION_HEADER, "header", True)
    assert parameter["schema"]["enum"] == list(SUPPORTED_API_VERSIONS)
