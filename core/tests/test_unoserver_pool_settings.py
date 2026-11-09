"""Tests reading the unoserver pool's settings from the environment."""

import pytest

from diplex.api import create_app
from diplex.api.unoserver_pool_settings import INSTANCE_COUNT_VARIABLE, WAIT_SECONDS_VARIABLE, read_unoserver_pool_settings
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


def test_a_docx_waits_30_seconds_for_an_instance_by_default(monkeypatch):
    """Without DIPLEX_CONVERTER_WAIT_SECONDS, a conversion waits up to 30 s for an idle instance."""
    monkeypatch.delenv(WAIT_SECONDS_VARIABLE, raising=False)

    assert read_unoserver_pool_settings().wait_seconds == 30


@pytest.mark.parametrize(("configured_value", "wait_seconds"), [("0", 0), ("90", 90)])
def test_the_wait_comes_from_the_environment(monkeypatch, configured_value, wait_seconds):
    """DIPLEX_CONVERTER_WAIT_SECONDS sets the wait in whole seconds; 0 means a busy pool answers at once."""
    monkeypatch.setenv(WAIT_SECONDS_VARIABLE, configured_value)

    assert read_unoserver_pool_settings().wait_seconds == wait_seconds


@pytest.mark.parametrize("configured_value", ["-1", "half a minute", "2.5"])
def test_a_wait_it_cannot_use_is_refused(monkeypatch, configured_value):
    """A negative or non-whole wait raises ValueError naming the variable."""
    monkeypatch.setenv(WAIT_SECONDS_VARIABLE, configured_value)

    with pytest.raises(ValueError, match=WAIT_SECONDS_VARIABLE):
        read_unoserver_pool_settings()
