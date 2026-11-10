"""The engine's FastAPI app; serve it with `uvicorn diplex.api:app`."""

from importlib.metadata import version

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from diplex.engine import UnoserverPool

from .api_key import ApiKeyRejectedError, answer_rejected_api_key, read_api_key
from .health_route import health_router
from .job_log import quiet_upload_parser_warnings, send_job_logs_to_stderr
from .openapi_spec import build_openapi_spec
from .render_route import render_router
from .request_errors import answer_http_error, answer_invalid_request
from .unoserver_pool_lifespan import run_unoserver_pool
from .unoserver_pool_settings import read_unoserver_pool_settings
from .upload_limit_setting import read_max_upload_bytes
from .upload_size_limit import UploadSizeLimit


def create_app(unoserver_pool: UnoserverPool | None = None) -> FastAPI:
    """Build the engine's FastAPI app: routes, API key, error answers, OpenAPI spec, upload limit, job logs and its pool."""
    engine_app = FastAPI(
        title="Diplex engine",
        summary="Renders each page of a DOCX or PDF as an image.",
        version=version("diplex-core"),
        exception_handlers={
            RequestValidationError: answer_invalid_request,
            HTTPException: answer_http_error,
            ApiKeyRejectedError: answer_rejected_api_key,
        },
        lifespan=run_unoserver_pool,
    )
    # The pool starts with the app, not here, so building an app (for its OpenAPI spec, say) starts no LibreOffice.
    engine_app.state.unoserver_pool = UnoserverPool(read_unoserver_pool_settings()) if unoserver_pool is None else unoserver_pool
    engine_app.state.api_key = read_api_key()  # None: authentication is off
    engine_app.include_router(health_router)
    engine_app.include_router(render_router)
    engine_app.add_middleware(UploadSizeLimit, max_upload_bytes=read_max_upload_bytes())
    send_job_logs_to_stderr()
    quiet_upload_parser_warnings()
    engine_app.openapi = lambda: build_openapi_spec(engine_app)
    return engine_app


app = create_app()

__all__ = ["app", "create_app"]
