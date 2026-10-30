"""Command line for the convention checker: `python -m scripts.conventions [--hook]`.

Without flags it prints the report and exits 1 when there are problems. With --hook, the mode the
Claude Code Stop hook uses, it prints the report to stderr and exits 2, which blocks the stop and
hands the report back to Claude to fix.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import check_repository, format_report

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HOOK_BLOCKING_EXIT_CODE = 2


def main() -> int:
    """Run the checker on the repository and return the process exit code."""
    parser = argparse.ArgumentParser(prog="python -m scripts.conventions", description=__doc__.splitlines()[0])
    parser.add_argument("--hook", action="store_true", help="Claude Code Stop hook mode: report on stderr, exit 2")
    arguments = parser.parse_args()
    violations = check_repository(REPOSITORY_ROOT)
    if not violations:
        if not arguments.hook:
            print("Convention check passed.")
        return 0
    report = format_report(REPOSITORY_ROOT, violations)
    if arguments.hook:
        print(report, file=sys.stderr)
        return HOOK_BLOCKING_EXIT_CODE
    print(report)
    return 1


if __name__ == "__main__":
    sys.exit(main())
