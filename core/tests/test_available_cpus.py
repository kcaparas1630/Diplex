"""Tests counting the vCPUs available to the engine from its CPU affinity and a cgroup v1 or v2 CPU quota."""

import os

import pytest

from diplex.engine import count_available_cpus


@pytest.fixture
def four_schedulable_cpus(monkeypatch):
    """Let the process run on four CPUs, whatever the test machine has."""
    monkeypatch.setattr(os, "sched_getaffinity", lambda process_id: {0, 1, 2, 3}, raising=False)


def _write_cgroup_v2_quota(cgroup_root, cpu_max: str) -> None:
    """Write cgroup v2's cpu.max, "<quota> <period>" or "max <period>"."""
    (cgroup_root / "cpu.max").write_text(f"{cpu_max}\n")


def _write_cgroup_v1_quota(cgroup_root, quota_microseconds: int, period_microseconds: int = 100000) -> None:
    """Write cgroup v1's cpu.cfs_quota_us and cpu.cfs_period_us, as docker run --cpus sets them."""
    cpu_folder = cgroup_root / "cpu"
    cpu_folder.mkdir()
    (cpu_folder / "cpu.cfs_quota_us").write_text(f"{quota_microseconds}\n")
    (cpu_folder / "cpu.cfs_period_us").write_text(f"{period_microseconds}\n")


def test_without_a_quota_it_counts_the_cpus_the_process_may_run_on(tmp_path, four_schedulable_cpus):
    """With no cgroup files, the count is the affinity's four CPUs."""
    assert count_available_cpus(tmp_path) == 4


@pytest.mark.parametrize(
    ("cpu_max", "expected_count"),
    [("max 100000", 4), ("200000 100000", 2), ("150000 100000", 2), ("20000 100000", 1), ("800000 100000", 4)],
    ids=["unlimited", "two", "one-and-a-half-rounds-up", "a-fifth-is-still-one", "quota-above-affinity"],
)
def test_a_cgroup_v2_quota_caps_the_count(tmp_path, four_schedulable_cpus, cpu_max, expected_count):
    """cpu.max caps the count, rounded up so a fractional quota still gets its last CPU, and never below 1."""
    _write_cgroup_v2_quota(tmp_path, cpu_max)

    assert count_available_cpus(tmp_path) == expected_count


@pytest.mark.parametrize(
    ("quota_microseconds", "expected_count"), [(-1, 4), (150000, 2), (300000, 3)], ids=["unlimited", "one-and-a-half", "three"]
)
def test_a_cgroup_v1_quota_caps_the_count(tmp_path, four_schedulable_cpus, quota_microseconds, expected_count):
    """cpu.cfs_quota_us over cpu.cfs_period_us caps the count; -1 means no quota (checked in a docker run --cpus=1.5)."""
    _write_cgroup_v1_quota(tmp_path, quota_microseconds)

    assert count_available_cpus(tmp_path) == expected_count


def test_an_unreadable_cpu_max_falls_back_to_cgroup_v1(tmp_path, four_schedulable_cpus):
    """A cpu.max that isn't "<quota> <period>" is ignored rather than trusted."""
    _write_cgroup_v2_quota(tmp_path, "garbled")
    _write_cgroup_v1_quota(tmp_path, 100000)

    assert count_available_cpus(tmp_path) == 1


def test_the_machine_has_at_least_one(tmp_path):
    """On the real machine, with no quota files, the count is a positive whole number."""
    assert count_available_cpus(tmp_path) >= 1
