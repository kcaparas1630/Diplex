"""The engine's HTTP API: the FastAPI app and its routes, the only way consumers reach the engine.

From core/, `uv run uvicorn diplex.api:app` serves it on 127.0.0.1:8000. health_route answers GET /health.
"""

from importlib.metadata import version

from fastapi import FastAPI

from .health_route import health_router


def create_app() -> FastAPI:
    """Build the engine's FastAPI app with every route attached."""
    engine_app = FastAPI(
        title="Diplex engine",
        summary="Renders a DOCX or PDF into an image of every page, plus the converted PDF for a DOCX.",
        version=version("diplex-core"),
    )
    engine_app.include_router(health_router)
    return engine_app


app = create_app()

__all__ = ["app", "create_app"]
