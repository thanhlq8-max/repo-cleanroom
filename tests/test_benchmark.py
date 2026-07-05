from pathlib import Path

import pytest

from repo_cleanroom.demo.benchmark import BenchmarkError, run_benchmark


def test_benchmark_runs_end_to_end(tmp_path: Path):
    result = run_benchmark(4, tmp_path)

    assert result["repo_count"] == 4
    assert result["synthetic_only"] is True
    assert result["scan_seconds"] >= 0
    assert result["plan_seconds"] >= 0
    assert (tmp_path / "bench-reports-4" / "cleanup_plan.json").exists()


def test_benchmark_refuses_reused_working_directory(tmp_path: Path):
    run_benchmark(2, tmp_path)

    with pytest.raises(BenchmarkError):
        run_benchmark(2, tmp_path)
