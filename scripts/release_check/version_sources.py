"""Reads the engine's version where the repository writes it: core/pyproject.toml and the published OpenAPI spec."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def read_package_version(repository_root: Path = REPOSITORY_ROOT) -> str:
    """The diplex-core package's version in core/pyproject.toml."""
    with (repository_root / "core" / "pyproject.toml").open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)["project"]["version"]


def read_published_spec_version(repository_root: Path = REPOSITORY_ROOT) -> str:
    """The version in docs/openapi.json, which the engine takes from its package."""
    return json.loads((repository_root / "docs" / "openapi.json").read_text(encoding="utf-8"))["info"]["version"]
