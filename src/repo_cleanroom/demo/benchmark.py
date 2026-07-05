"""Benchmark the scan and plan pipeline against a synthetic workspace.

Generates a demo workspace of a requested size in a caller-selected working
directory, then times `scan` and `plan`. Everything is synthetic; the only
writes happen inside the caller-selected directory.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.cli import main as cli_main
from repo_cleanroom.demo.workspace_generator import DemoWorkspaceError, generate_demo_workspace

BENCHMARK_SCHEMA_VERSION = "0.7.0"


class BenchmarkError(ValueError):
    """Raised when the benchmark cannot run safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_benchmark(repo_count: int, work_dir: str | Path) -> dict[str, Any]:
    """Generate, scan, and plan a synthetic workspace; return timing results."""

    base = Path(work_dir).expanduser()
    workspace = base / f"bench-workspace-{repo_count}"
    reports = base / f"bench-reports-{repo_count}"
    if workspace.exists() or reports.exists():
        raise BenchmarkError(
            f"benchmark paths already exist under {base}; use a fresh working directory"
        )

    try:
        generate_demo_workspace(workspace, repo_count=repo_count)
    except DemoWorkspaceError as exc:
        raise BenchmarkError(str(exc)) from exc

    started_scan = time.perf_counter()
    scan_exit = cli_main(["scan", "--root", str(workspace), "--out-dir", str(reports)])
    scan_seconds = time.perf_counter() - started_scan
    if scan_exit != 0:
        raise BenchmarkError(f"scan failed with exit code {scan_exit}")

    started_plan = time.perf_counter()
    plan_exit = cli_main(
        [
            "plan",
            "--scan-artifacts",
            str(reports / "artifact_inventory.json"),
            "--out-dir",
            str(reports),
        ]
    )
    plan_seconds = time.perf_counter() - started_plan
    if plan_exit != 0:
        raise BenchmarkError(f"plan failed with exit code {plan_exit}")

    return {
        "benchmark_schema_version": BENCHMARK_SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "repo_count": repo_count,
        "workspace": str(workspace),
        "scan_seconds": round(scan_seconds, 3),
        "plan_seconds": round(plan_seconds, 3),
        "synthetic_only": True,
    }
