"""Writes the engine's OpenAPI spec to a file: `python -m diplex.openapi_export ../docs/openapi.json`."""

import json
import sys
from pathlib import Path

from diplex.api import create_app


def write_openapi_spec(spec_path: Path) -> None:
    """Write the spec as indented JSON ending in a newline, so the published copy diffs cleanly."""
    spec_text = json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"
    spec_path.write_text(spec_text, encoding="utf-8")


if __name__ == "__main__":
    write_openapi_spec(Path(sys.argv[1]))
