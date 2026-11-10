"""Reads the optional static API key from the DIPLEX_API_KEY environment variable (ADR 012)."""

import os

API_KEY_VARIABLE = "DIPLEX_API_KEY"
MIN_API_KEY_LENGTH = 16  # a shorter key is too easy to guess; `openssl rand -hex 32` gives 64 characters


def read_api_key() -> str | None:
    """Return the key from DIPLEX_API_KEY, or None when it is unset or empty, so authentication is off."""
    configured_key = os.environ.get(API_KEY_VARIABLE, "").strip()
    if not configured_key:
        return None
    if len(configured_key) < MIN_API_KEY_LENGTH:
        raise ValueError(f"{API_KEY_VARIABLE} must be at least {MIN_API_KEY_LENGTH} characters long")
    return configured_key
