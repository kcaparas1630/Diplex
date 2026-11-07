"""Reads the unoserver pool's settings from DIPLEX_* environment variables, refusing values it can't use."""

import os

from diplex.engine import UnoserverPoolSettings

INSTANCE_COUNT_VARIABLE = "DIPLEX_UNOSERVER_INSTANCES"
DEFAULT_INSTANCE_COUNT = 1


def read_unoserver_pool_settings() -> UnoserverPoolSettings:
    """Return the pool settings from the environment, with the defaults for variables that are not set."""
    return UnoserverPoolSettings(
        instance_count=_read_whole_number(INSTANCE_COUNT_VARIABLE, DEFAULT_INSTANCE_COUNT, minimum=1),
    )


def _read_whole_number(variable_name: str, default: int, *, minimum: int) -> int:
    """Read a whole-number variable, or the default when it is unset; raise ValueError when it is not one or too small."""
    configured_value = os.environ.get(variable_name, "").strip()
    if not configured_value:
        return default
    if not configured_value.isdecimal() or int(configured_value) < minimum:
        raise ValueError(f"{variable_name} must be a whole number of at least {minimum}, not {configured_value!r}")
    return int(configured_value)
