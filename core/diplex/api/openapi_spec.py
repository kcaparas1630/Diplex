"""Builds the OpenAPI spec, with /render's success response as multipart/form-data, which FastAPI can't say alone."""

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
        engine_app.openapi_schema = openapi_spec
    return engine_app.openapi_schema
