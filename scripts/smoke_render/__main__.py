"""Command line for the smoke test: `python -m scripts.smoke_render <engine URL> [samples folder]`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import format_results_table, render_samples

DEFAULT_SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"


def main() -> int:
    """Render every sample, print progress on stderr and the table on stdout; exit 1 if any sample failed."""
    parser = argparse.ArgumentParser(prog="python -m scripts.smoke_render", description=__doc__)
    parser.add_argument("engine_url", help="the running engine, e.g. http://127.0.0.1:8000")
    parser.add_argument("samples_folder", nargs="?", type=Path, default=DEFAULT_SAMPLES_FOLDER)
    arguments = parser.parse_args()
    results = render_samples(
        arguments.engine_url,
        arguments.samples_folder,
        on_result=lambda result: print(f"{result.sample_name}: {result.outcome}", file=sys.stderr, flush=True),
    )
    print(format_results_table(results))
    return 0 if all(result.outcome == "ok" for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
