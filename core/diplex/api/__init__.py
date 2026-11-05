"""The engine's FastAPI app; serve it with `uvicorn diplex.api:app`."""

from importlib.metadata import version

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from .health_route import health_router
from .job_log import quiet_upload_parser_warnings, send_job_logs_to_stderr
from .openapi_spec import build_openapi_spec
from .render_route import render_router
from .request_errors import answer_http_error, answer_invalid_request
from .upload_limit_setting import read_max_upload_bytes
from .upload_size_limit import UploadSizeLimit


def create_app() -> FastAPI:
    """Build the engine's FastAPI app: routes, error answers, OpenAPI spec, upload limit and job logs on stderr."""
    engine_app = FastAPI(
        title="Diplex engine",
        summary="Renders each page of a DOCX or PDF as an image.",
        version=version("diplex-core"),
        exception_handlers={RequestValidationError: answer_invalid_request, HTTPException: answer_http_error},
    )
    engine_app.include_router(health_router)
    engine_app.include_router(render_router)
    engine_app.add_middleware(UploadSizeLimit, max_upload_bytes=read_max_upload_bytes())
    send_job_logs_to_stderr()
    quiet_upload_parser_warnings()
    engine_app.openapi = lambda: build_openapi_spec(engine_app)
    return engine_app


app = create_app()

__all__ = ["app", "create_app"]
