"""Reads the version out of a release tag: v1.2.3 is version 1.2.3; anything else is not a release tag."""

from __future__ import annotations

import re

RELEASE_TAG_PATTERN = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")  # SemVer's core, no pre-release


def parse_release_tag(release_tag: str) -> str | None:
    """Return the version a tag like v1.2.3 names, or None for anything that isn't one."""
    match = RELEASE_TAG_PATTERN.match(release_tag)
    return None if match is None else ".".join(match.groups())
