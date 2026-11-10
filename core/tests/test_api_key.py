"""Tests the optional static API key: off without DIPLEX_API_KEY, required as a Bearer token on /render with it."""

import pytest
from fastapi.testclient import TestClient

from diplex.api import create_app
from diplex.api.api_key import API_KEY_VARIABLE, read_api_key
from diplex.definition import API_VERSION_HEADER, CURRENT_API_VERSION, RenderErrorCode
from stand_in_unoserver_pool import StandInUnoserverPool

ENGINE_KEY = "test-key-0123456789abcdef"
NOT_A_DOCUMENT = b"plain text, not a document"


VERSION_HEADERS = {API_VERSION_HEADER: CURRENT_API_VERSION}  # every /render request sends it (ADR 012)


def _post_render(headers: dict[str, str]):
    """Send a non-document to /render with the given headers; a request that gets past the key gets 415."""
    with TestClient(create_app(unoserver_pool=StandInUnoserverPool()), headers=VERSION_HEADERS) as client:
        return client.post("/render", files={"document": ("upload.txt", NOT_A_DOCUMENT)}, headers=headers)


@pytest.fixture
def engine_with_key(monkeypatch):
    """Start apps in the test with DIPLEX_API_KEY set."""
    monkeypatch.setenv(API_KEY_VARIABLE, ENGINE_KEY)


def test_without_a_key_no_authentication_is_needed(monkeypatch):
    """With DIPLEX_API_KEY unset, a request without Authorization reaches the render step."""
    monkeypatch.delenv(API_KEY_VARIABLE, raising=False)

    assert _post_render({}).status_code == 415


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong-key-0123456789"}, {"Authorization": f"Basic {ENGINE_KEY}"}, {"Authorization": "Bearer"}],
    ids=["missing", "wrong-key", "not-bearer", "empty-token"],
)
def test_with_a_key_a_request_without_it_gets_401(engine_with_key, headers):
    """A missing, wrong or non-Bearer key gets 401 unauthorized, with the Bearer challenge and no rendering."""
    response = _post_render(headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["code"] == RenderErrorCode.UNAUTHORIZED
    assert ENGINE_KEY not in response.text


def test_with_a_key_the_right_bearer_token_gets_through(engine_with_key):
    """The engine's key as `Authorization: Bearer <key>` gets past the check (here to the 415 for a text file)."""
    assert _post_render({"Authorization": f"Bearer {ENGINE_KEY}"}).status_code == 415


def test_health_stays_open_with_a_key(engine_with_key):
    """GET /health needs no key, so container health checks keep working."""
    with TestClient(create_app(unoserver_pool=StandInUnoserverPool()), headers=VERSION_HEADERS) as client:
        assert client.get("/health").status_code == 200


@pytest.mark.parametrize(("configured_key", "expected_key"), [("", None), ("   ", None), (f" {ENGINE_KEY} ", ENGINE_KEY)])
def test_the_key_is_read_from_the_environment(monkeypatch, configured_key, expected_key):
    """An empty variable leaves authentication off; surrounding spaces are not part of the key."""
    monkeypatch.setenv(API_KEY_VARIABLE, configured_key)

    assert read_api_key() == expected_key


def test_a_short_key_stops_the_engine_at_startup(monkeypatch):
    """A key under 16 characters is refused when the engine starts, instead of running with a guessable key."""
    monkeypatch.setenv(API_KEY_VARIABLE, "short")

    with pytest.raises(ValueError, match=API_KEY_VARIABLE):
        create_app()


def test_the_spec_says_the_key_is_an_optional_bearer_token():
    """/render lists the ApiKey Bearer scheme and an empty requirement, so the key is documented as optional."""
    openapi_spec = create_app(unoserver_pool=StandInUnoserverPool()).openapi()

    assert openapi_spec["components"]["securitySchemes"]["ApiKey"]["scheme"] == "bearer"
    assert openapi_spec["paths"]["/render"]["post"]["security"] == [{"ApiKey": []}, {}]
    assert "401" in openapi_spec["paths"]["/render"]["post"]["responses"]
    assert "security" not in openapi_spec["paths"]["/health"]["get"]
