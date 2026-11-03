"""The GET /health response body."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """{"status": "ok"} while the engine is up."""

    status: Literal["ok"] = Field(default="ok", description="Always ok.")
