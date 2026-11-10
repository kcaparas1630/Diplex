"""Release check: a release tag must match the engine's version everywhere it is written (convention 011).

Run it with `python -m scripts.release_check v1.2.3`; it needs only the standard library.
"""

from __future__ import annotations

from .version_sources import read_package_version, read_published_spec_version
from .version_tag import parse_release_tag

__all__ = ["check_release", "parse_release_tag", "read_package_version", "read_published_spec_version"]


def check_release(release_tag: str, package_version: str, published_spec_version: str) -> list[str]:
    """Return every problem with releasing this tag; an empty list means the tag can be released."""
    tag_version = parse_release_tag(release_tag)
    if tag_version is None:
        return [f"{release_tag!r} is not a release tag like v1.2.3"]
    problems = []
    if package_version != tag_version:
        problems.append(f"core/pyproject.toml says {package_version}, the tag says {tag_version}")
    if published_spec_version != package_version:
        problems.append(
            f"docs/openapi.json says {published_spec_version}; regenerate it with diplex.openapi_export after the bump"
        )
    return problems
