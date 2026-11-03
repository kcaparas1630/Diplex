"""The engine's FastAPI app; serve it with `uvicorn diplex.api:app`."""

from importlib.metadata import version

from fastapi import FastAPI

from .health_route import health_router


def create_app() -> FastAPI:
    """Build the engine's FastAPI app."""
    engine_app = FastAPI(
        title="Diplex engine",
        summary="Renders each page of a DOCX or PDF as an image.",
        version=version("diplex-core"),
    )
    engine_app.include_router(health_router)
    return engine_app


app = create_app()

__all__ = ["app", "create_app"]
