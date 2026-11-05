"""Unit tests for reading the upload size limit from DIPLEX_MAX_UPLOAD_BYTES."""

import pytest

from diplex.api.upload_limit_setting import DEFAULT_MAX_UPLOAD_BYTES, MAX_UPLOAD_BYTES_VARIABLE, read_max_upload_bytes


def test_the_default_is_50_mib_when_the_variable_is_not_set(monkeypatch):
    """With no variable set, the limit is the provisional 50 MiB."""
    monkeypatch.delenv(MAX_UPLOAD_BYTES_VARIABLE, raising=False)

    assert read_max_upload_bytes() == DEFAULT_MAX_UPLOAD_BYTES == 52_428_800


def test_an_empty_variable_means_the_default(monkeypatch):
    """A variable set to nothing, as `DIPLEX_MAX_UPLOAD_BYTES=` in a compose file gives, keeps the default."""
    monkeypatch.setenv(MAX_UPLOAD_BYTES_VARIABLE, " ")

    assert read_max_upload_bytes() == DEFAULT_MAX_UPLOAD_BYTES


def test_the_variable_sets_the_limit_in_bytes(monkeypatch):
    """A whole number of bytes becomes the limit."""
    monkeypatch.setenv(MAX_UPLOAD_BYTES_VARIABLE, "10485760")

    assert read_max_upload_bytes() == 10_485_760


@pytest.mark.parametrize("configured_limit", ["50MB", "-1", "0", "1.5", "1e6", "ten"])
def test_anything_but_a_positive_whole_number_is_refused_at_startup(monkeypatch, configured_limit):
    """A limit the engine can't read stops it starting, instead of running with a limit nobody chose."""
    monkeypatch.setenv(MAX_UPLOAD_BYTES_VARIABLE, configured_limit)

    with pytest.raises(ValueError, match=f"{MAX_UPLOAD_BYTES_VARIABLE} must be a whole number of bytes above 0"):
        read_max_upload_bytes()
