"""GET /health: tells a container runtime or load balancer that the engine process is up and answering.

It does not check unoserver. Whether the LibreOffice pool can take work is a readiness question for the pool
(ADR 004), not for this liveness check.
"""

from fastapi import APIRouter

from diplex.definition import HealthStatus

health_router = APIRouter(tags=["health"])


@health_router.get("/health", summary="Check that the engine is up")
def report_health() -> HealthStatus:
    """Answer 200 with {"status": "ok"} for as long as the process is running."""
    return HealthStatus()
