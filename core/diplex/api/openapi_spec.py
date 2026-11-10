"""Builds the OpenAPI spec, with what FastAPI can't say alone: /render's multipart success, optional key and required version."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from diplex.definition import API_VERSION_HEADER, SUPPORTED_API_VERSIONS

RENDER_PATH = "/render"


def build_openapi_spec(engine_app: FastAPI) -> dict:
    """Generate the spec once, then file /render's 200 schema under multipart/form-data instead of application/json."""
    if engine_app.openapi_schema is None:
        openapi_spec = get_openapi(
            title=engine_app.title,
            version=engine_app.version,
            summary=engine_app.summary,
            routes=engine_app.routes,
        )
        # FastAPI files every response model under one media type per route; the errors stay JSON.
        success_response = openapi_spec["paths"][RENDER_PATH]["post"]["responses"]["200"]
        success_response["content"] = {"multipart/form-data": success_response["content"]["application/json"]}
        # The key is needed only when the engine has one; an empty requirement makes it optional (OpenAPI 3.1, Security Requirement Object).
        openapi_spec["paths"][RENDER_PATH]["post"]["security"].append({})
        # The header is optional in Python only so a missing one gets unsupported_api_version, not FastAPI's 422.
        for parameter in openapi_spec["paths"][RENDER_PATH]["post"]["parameters"]:
            if parameter["name"] == API_VERSION_HEADER:
                parameter["required"] = True
                parameter["schema"] = {"type": "string", "enum": list(SUPPORTED_API_VERSIONS)}
        engine_app.openapi_schema = openapi_spec
    return engine_app.openapi_schema
