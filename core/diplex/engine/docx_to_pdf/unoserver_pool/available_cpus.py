"""Counts the vCPUs the engine may use: the CPUs it may run on, capped by the container's CPU quota (docker run --cpus)."""

import math
import os
from pathlib import Path

CGROUP_ROOT = Path("/sys/fs/cgroup")  # a container sees its own cgroup here


def count_available_cpus(cgroup_root: Path = CGROUP_ROOT) -> int:
    """Return the CPUs this process may run on, capped by any cgroup CPU quota rounded up, and at least 1."""
    cpu_count = _count_schedulable_cpus()
    cpu_quota = _read_cgroup_cpu_quota(cgroup_root)
    if cpu_quota is not None:
        cpu_count = min(cpu_count, max(1, math.ceil(cpu_quota)))
    return cpu_count


def _count_schedulable_cpus() -> int:
    """The CPUs the scheduler lets this process use (its affinity), or the machine's CPUs where that isn't known."""
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0))  # os.cpu_count() counts the machine's CPUs, usable or not
    return os.cpu_count() or 1


def _read_cgroup_cpu_quota(cgroup_root: Path) -> float | None:
    """The CPU quota in CPUs, from cgroup v2's cpu.max or v1's cpu.cfs_quota_us, or None when there is none."""
    try:
        quota_text, period_text = (cgroup_root / "cpu.max").read_text().split()  # v2: "150000 100000" or "max 100000"
        return None if quota_text == "max" else int(quota_text) / int(period_text)
    except (OSError, ValueError):
        pass
    try:
        quota_microseconds = int((cgroup_root / "cpu" / "cpu.cfs_quota_us").read_text())  # v1: -1 when unlimited
        period_microseconds = int((cgroup_root / "cpu" / "cpu.cfs_period_us").read_text())
    except (OSError, ValueError):
        return None
    return None if quota_microseconds < 0 else quota_microseconds / period_microseconds
