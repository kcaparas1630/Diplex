"""Command line for the load test: `python -m scripts.load_test <engine URL> [samples folder] --concurrency N`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.smoke_render import render_sample

from . import PeakMemorySampler, format_load_report, read_container_memory, run_load_test

DEFAULT_SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"


def main() -> int:
    """Warm the engine up, run the load test, print progress on stderr and the report on stdout; exit 1 on any failure."""
    parser = argparse.ArgumentParser(prog="python -m scripts.load_test", description=__doc__)
    parser.add_argument("engine_url", help="the running engine, e.g. http://127.0.0.1:8000")
    parser.add_argument("samples_folder", nargs="?", type=Path, default=DEFAULT_SAMPLES_FOLDER)
    parser.add_argument("--concurrency", type=int, default=1, help="renders in flight at once (default 1)")
    parser.add_argument("--rounds", type=int, default=1, help="times each sample is sent (default 1)")
    parser.add_argument("--container", help="the engine's Docker container name, to sample its peak memory")
    arguments = parser.parse_args()
    sample_paths = sorted(path for path in arguments.samples_folder.iterdir() if path.suffix.lower() == ".docx")
    if not sample_paths:
        print(f"no DOCX samples in {arguments.samples_folder}", file=sys.stderr)
        return 1
    # Not timed: the first DOCX waits for LibreOffice to start.
    render_sample(arguments.engine_url, sample_paths[0])
    memory_sampler = None
    if arguments.container:
        memory_sampler = PeakMemorySampler(lambda: read_container_memory(arguments.container))
        memory_sampler.start()
    renders, wall_seconds = run_load_test(
        arguments.engine_url,
        sample_paths,
        arguments.concurrency,
        arguments.rounds,
        on_render=lambda render: print(f"{render.sample_name}: {render.outcome} {render.seconds:.2f} s", file=sys.stderr, flush=True),
    )
    peak_memory_bytes = memory_sampler.stop() if memory_sampler else None
    print(
        f"{len(sample_paths)} DOCX samples x {arguments.rounds} rounds = {len(renders)} renders "
        f"against {arguments.engine_url}\n"
    )
    print(format_load_report(renders, wall_seconds, arguments.concurrency, peak_memory_bytes))
    return 0 if all(render.outcome == "ok" for render in renders) else 1


if __name__ == "__main__":
    sys.exit(main())
