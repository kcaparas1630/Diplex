"""Tests the release check: tags, versions in the repository, and the problems it reports."""

from __future__ import annotations

import subprocess
import sys

import pytest

from scripts.release_check import check_release, parse_release_tag, read_package_version, read_published_spec_version


@pytest.mark.parametrize(
    ("release_tag", "expected_version"),
    [("v0.1.0", "0.1.0"), ("v12.3.45", "12.3.45"), ("0.1.0", None), ("v1.2", None), ("v01.2.3", None), ("v1.2.3-rc.1", None)],
)
def test_only_plain_semver_tags_are_release_tags(release_tag, expected_version):
    """v plus MAJOR.MINOR.PATCH is a release tag; no v, missing parts, leading zeros and pre-releases are not."""
    assert parse_release_tag(release_tag) == expected_version


def test_a_matching_tag_has_no_problems():
    """A tag that matches both versions can be released."""
    assert check_release("v1.4.0", "1.4.0", "1.4.0") == []


def test_every_mismatch_is_reported():
    """A tag ahead of the package, and a spec not regenerated, are both named."""
    problems = check_release("v1.5.0", "1.4.0", "1.3.0")

    assert problems == [
        "core/pyproject.toml says 1.4.0, the tag says 1.5.0",
        "docs/openapi.json says 1.3.0; regenerate it with diplex.openapi_export after the bump",
    ]


def test_a_tag_that_is_not_a_release_tag_is_refused():
    """A branch-like or malformed tag is refused outright."""
    assert check_release("main", "1.4.0", "1.4.0") == ["'main' is not a release tag like v1.2.3"]


def test_the_repository_versions_agree_today():
    """core/pyproject.toml and docs/openapi.json carry the same version on main."""
    assert read_package_version() == read_published_spec_version()


def test_the_command_line_exits_1_on_a_mismatch_and_0_on_a_match():
    """The workflow relies on the exit code: 1 with the reason on stderr, 0 when the tag matches."""
    current_tag = f"v{read_package_version()}"

    matching = subprocess.run([sys.executable, "-m", "scripts.release_check", current_tag], capture_output=True, text=True)
    mismatching = subprocess.run([sys.executable, "-m", "scripts.release_check", "v999.0.0"], capture_output=True, text=True)

    assert (matching.returncode, mismatching.returncode) == (0, 1)
    assert "the tag says 999.0.0" in mismatching.stderr
