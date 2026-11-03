"""GET /health: 200 while the engine process is up. It doesn't check unoserver."""

from fastapi import APIRouter

from diplex.definition import HealthStatus

health_router = APIRouter(tags=["health"])


@health_router.get("/health", summary="Check that the engine is up")
def report_health() -> HealthStatus:
    """Report that the engine is up."""
    return HealthStatus()
