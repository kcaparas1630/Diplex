"""Builds the OpenAPI spec, with what FastAPI can't say alone: /render's multipart/form-data success and its optional API key."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

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
        engine_app.openapi_schema = openapi_spec
    return engine_app.openapi_schema
