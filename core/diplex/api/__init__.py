"""The engine's FastAPI app; serve it with `uvicorn diplex.api:app`."""

from importlib.metadata import version

from fastapi import FastAPI

from .health_route import health_router
from .upload_limit_setting import read_max_upload_bytes
from .upload_size_limit import UploadSizeLimit


def create_app() -> FastAPI:
    """Build the engine's FastAPI app, with the upload limit from DIPLEX_MAX_UPLOAD_BYTES."""
    engine_app = FastAPI(
        title="Diplex engine",
        summary="Renders each page of a DOCX or PDF as an image.",
        version=version("diplex-core"),
    )
    engine_app.include_router(health_router)
    engine_app.add_middleware(UploadSizeLimit, max_upload_bytes=read_max_upload_bytes())
    return engine_app


app = create_app()

__all__ = ["app", "create_app"]
