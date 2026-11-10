"""GET /health: 200 while the engine process is up. It doesn't check unoserver, and it never waits for a request thread."""

from fastapi import APIRouter

from diplex.definition import HealthStatus

health_router = APIRouter(tags=["health"])


@health_router.get("/health", summary="Check that the engine is up")
async def report_health() -> HealthStatus:
    """Report that the engine is up, on the event loop, so busy render threads can't hold it up."""
    return HealthStatus()
