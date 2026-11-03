"""The body of a GET /health response."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(BaseModel):
    """What GET /health returns while the engine process is up: {"status": "ok"}."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = Field(default="ok", description="Always ok; an engine that is down does not answer.")
