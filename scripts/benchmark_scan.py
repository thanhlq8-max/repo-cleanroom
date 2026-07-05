"""Run the synthetic scan/plan benchmark.

Usage (from a checkout with repo-cleanroom installed):

    py scripts/benchmark_scan.py --repo-count 100 --work-dir C:\\path\\to\\empty\\dir

The working directory must be fresh; the script writes only inside it and
deletes nothing. All workspace content is synthetic.
"""

from __future__ import annotations

import argparse
import json
import sys

from repo_cleanroom.demo.benchmark import BenchmarkError, run_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark repo-cleanroom scan/plan.")
    parser.add_argument("--repo-count", type=int, required=True, help="synthetic repos to generate")
    parser.add_argument("--work-dir", required=True, help="fresh working directory for the run")
    args = parser.parse_args(argv)

    try:
        result = run_benchmark(args.repo_count, args.work_dir)
    except BenchmarkError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
