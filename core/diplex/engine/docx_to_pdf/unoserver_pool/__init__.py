"""The engine's pool of unoserver instances (ADR 011): pooled_instance/ keeps one instance running, unoserver_pool.py
starts N of them and hands out conversions, and available_cpus.py counts the vCPUs that size the pool by default."""

from .available_cpus import count_available_cpus
from .pooled_instance import InstanceState
from .unoserver_pool import (
    FIRST_UNOSERVER_PORT,
    ConverterBusyError,
    UnoserverPool,
    UnoserverPoolSettings,
    unoserver_pool_logger,
)

__all__ = [
    "FIRST_UNOSERVER_PORT",
    "ConverterBusyError",
    "InstanceState",
    "UnoserverPool",
    "UnoserverPoolSettings",
    "count_available_cpus",
    "unoserver_pool_logger",
]
