"""Tests the engine's OpenAPI spec: /render's multipart/form-data request and response, its errors, and the published copy."""

import json
from pathlib import Path

import pytest

from diplex.api import create_app
from diplex.definition import RenderErrorCode, RenderPart
from diplex.openapi_export import write_openapi_spec

PUBLISHED_SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
ERROR_STATUSES = ["400", "401", "413", "415", "422", "500", "503"]


@pytest.fixture(scope="module")
def openapi_spec() -> dict:
    """The spec the engine serves at /openapi.json."""
    return create_app().openapi()


def _render_operation(openapi_spec: dict) -> dict:
    """The POST /render operation in the spec."""
    return openapi_spec["paths"]["/render"]["post"]


def _component(openapi_spec: dict, reference: dict) -> dict:
    """Follow a $ref to its schema in the spec's components."""
    return openapi_spec["components"]["schemas"][reference["$ref"].removeprefix("#/components/schemas/")]


def test_the_published_spec_is_the_one_the_engine_serves(openapi_spec):
    """docs/openapi.json is up to date; if this fails, run `cd core && uv run python -m diplex.openapi_export ../docs/openapi.json`."""
    assert json.loads(PUBLISHED_SPEC_PATH.read_text(encoding="utf-8")) == openapi_spec


def test_the_request_is_multipart_with_a_required_document_file(openapi_spec):
    """The upload is multipart/form-data with one required binary part, document, and the DOCX and PDF types to send."""
    request_content = _render_operation(openapi_spec)["requestBody"]["content"]
    upload_schema = _component(openapi_spec, request_content["multipart/form-data"]["schema"])

    assert list(request_content) == ["multipart/form-data"]
    assert upload_schema["required"] == ["document"]
    assert upload_schema["properties"]["document"]["type"] == "string"
    assert "application/pdf" in request_content["multipart/form-data"]["encoding"]["document"]["contentType"]


def test_success_is_multipart_with_the_parts_consumers_read(openapi_spec):
    """200 is multipart/form-data only; its parts are manifest (JSON), page (WebP images) and pdf (optional)."""
    success_content = _render_operation(openapi_spec)["responses"]["200"]["content"]
    parts_schema = _component(openapi_spec, success_content["multipart/form-data"]["schema"])

    assert list(success_content) == ["multipart/form-data"]
    assert list(parts_schema["properties"]) == [part.value for part in RenderPart]
    assert parts_schema["required"] == ["manifest", "page"]
    assert parts_schema["properties"]["manifest"]["$ref"] == "#/components/schemas/RenderManifest"
    assert parts_schema["properties"]["page"]["items"] == {"type": "string", "contentMediaType": "image/webp"}
    assert parts_schema["properties"]["pdf"]["contentMediaType"] == "application/pdf"


@pytest.mark.parametrize("status", ERROR_STATUSES)
def test_every_error_is_a_json_render_error(openapi_spec, status):
    """Each error status /render can answer is described as a RenderError in JSON."""
    error_content = _render_operation(openapi_spec)["responses"][status]["content"]

    assert error_content == {"application/json": {"schema": {"$ref": "#/components/schemas/RenderError"}}}


def test_the_spec_lists_every_error_code(openapi_spec):
    """Consumers generating code from the spec see every code they may get."""
    assert openapi_spec["components"]["schemas"]["RenderErrorCode"]["enum"] == [code.value for code in RenderErrorCode]


def test_fastapis_validation_error_shape_is_not_promised(openapi_spec):
    """The engine answers bad requests with RenderError, so the spec doesn't describe FastAPI's own shape."""
    assert "HTTPValidationError" not in openapi_spec["components"]["schemas"]


def test_the_command_writes_the_spec_as_json(tmp_path, openapi_spec):
    """write_openapi_spec writes the served spec, indented and ending in a newline."""
    spec_path = tmp_path / "openapi.json"

    write_openapi_spec(spec_path)

    spec_text = spec_path.read_text(encoding="utf-8")
    assert json.loads(spec_text) == openapi_spec
    assert spec_text.startswith('{\n  "openapi": "3.1')
    assert spec_text.endswith("}\n")
