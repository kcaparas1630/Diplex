"""Reads the unoserver pool's settings from DIPLEX_* environment variables, refusing values it can't use."""

import os

from diplex.engine import UnoserverPoolSettings, count_available_cpus

INSTANCE_COUNT_VARIABLE = "DIPLEX_UNOSERVER_INSTANCES"  # by default one per vCPU: more slowed every conversion (ADR 004)
WAIT_SECONDS_VARIABLE = "DIPLEX_CONVERTER_WAIT_SECONDS"  # how long a DOCX waits for an idle instance; 0 is no wait
DEFAULT_WAIT_SECONDS = 30
TIMEOUT_SECONDS_VARIABLE = "DIPLEX_CONVERSION_TIMEOUT_SECONDS"  # then the instance is killed and the DOCX gets 422
DEFAULT_TIMEOUT_SECONDS = 120
RECYCLE_COUNT_VARIABLE = "DIPLEX_CONVERSIONS_BEFORE_RECYCLE"  # LibreOffice's memory only grows (ADR 004)
DEFAULT_RECYCLE_COUNT = 50


def read_unoserver_pool_settings() -> UnoserverPoolSettings:
    """Return the pool settings from the environment, with the defaults for variables that are not set."""
    return UnoserverPoolSettings(
        instance_count=_read_whole_number(INSTANCE_COUNT_VARIABLE, count_available_cpus(), minimum=1),
        wait_seconds=_read_whole_number(WAIT_SECONDS_VARIABLE, DEFAULT_WAIT_SECONDS, minimum=0),
        conversion_timeout_seconds=_read_whole_number(TIMEOUT_SECONDS_VARIABLE, DEFAULT_TIMEOUT_SECONDS, minimum=1),
        conversions_before_recycle=_read_whole_number(RECYCLE_COUNT_VARIABLE, DEFAULT_RECYCLE_COUNT, minimum=1),
    )


def _read_whole_number(variable_name: str, default: int, *, minimum: int) -> int:
    """Read a whole-number variable, or the default when it is unset; raise ValueError when it is not one or too small."""
    configured_value = os.environ.get(variable_name, "").strip()
    if not configured_value:
        return default
    if not configured_value.isdecimal() or int(configured_value) < minimum:
        raise ValueError(f"{variable_name} must be a whole number of at least {minimum}, not {configured_value!r}")
    return int(configured_value)
