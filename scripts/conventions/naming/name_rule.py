"""The naming rule from convention 009: a name must say what it holds or does."""

from __future__ import annotations

from ..settings import ALLOWED_SHORT_NAMES, IGNORED_NAMES, MIN_NAME_LENGTH, VAGUE_NAMES


def name_problem(name: str) -> str | None:
    """Explain why a name is unclear, or return None when it is clear enough."""
    if name in IGNORED_NAMES:
        return None
    core = name.strip("_")
    if not core:
        return None
    word = core.rstrip("0123456789").lower()
    if word in VAGUE_NAMES:
        return f"`{name}` is vague; name what it holds or does"
    if len(core) < MIN_NAME_LENGTH and core.lower() not in ALLOWED_SHORT_NAMES:
        return f"`{name}` is too short to say what it is"
    return None
