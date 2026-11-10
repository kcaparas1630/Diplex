"""Command line for the release check: `python -m scripts.release_check <tag>`; exits 1 and says why when it can't be released."""

from __future__ import annotations

import sys

from . import check_release, read_package_version, read_published_spec_version


def main() -> int:
    """Check the tag given on the command line against the repository's versions."""
    if len(sys.argv) != 2:
        print("usage: python -m scripts.release_check v1.2.3", file=sys.stderr)
        return 2
    problems = check_release(sys.argv[1], read_package_version(), read_published_spec_version())
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"{sys.argv[1]} matches core/pyproject.toml and docs/openapi.json")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
