"""Tests reading the unoserver pool's settings from the environment."""

import pytest

from diplex.api import create_app
from diplex.api.unoserver_pool_settings import INSTANCE_COUNT_VARIABLE, read_unoserver_pool_settings
from diplex.engine import count_available_cpus


def test_one_instance_per_available_vcpu_by_default(monkeypatch):
    """Without DIPLEX_UNOSERVER_INSTANCES, the pool runs one instance per vCPU available to the engine."""
    monkeypatch.delenv(INSTANCE_COUNT_VARIABLE, raising=False)

    assert read_unoserver_pool_settings().instance_count == count_available_cpus()


def test_the_instance_count_comes_from_the_environment(monkeypatch):
    """DIPLEX_UNOSERVER_INSTANCES sets the number of instances."""
    monkeypatch.setenv(INSTANCE_COUNT_VARIABLE, " 4 ")

    assert read_unoserver_pool_settings().instance_count == 4


@pytest.mark.parametrize("configured_value", ["0", "-2", "two", "1.5"])
def test_an_instance_count_it_cannot_use_is_refused(monkeypatch, configured_value):
    """Zero, negative or non-whole instance counts raise ValueError naming the variable."""
    monkeypatch.setenv(INSTANCE_COUNT_VARIABLE, configured_value)

    with pytest.raises(ValueError, match=INSTANCE_COUNT_VARIABLE):
        read_unoserver_pool_settings()


def test_the_engine_refuses_to_start_with_an_unreadable_instance_count(monkeypatch):
    """An engine started with an instance count it can't read fails at once, instead of guessing."""
    monkeypatch.setenv(INSTANCE_COUNT_VARIABLE, "many")

    with pytest.raises(ValueError, match=INSTANCE_COUNT_VARIABLE):
        create_app()
