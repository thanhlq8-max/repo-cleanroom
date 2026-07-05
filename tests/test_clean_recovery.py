"""v0.3.1: dry-run parity, partial failure reporting, rollback-not-claimed policy."""

import json
from pathlib import Path

from repo_cleanroom.cli import main

from test_clean_command import _clean_args, _make_workspace, _scan_plan_approve


def test_dry_run_and_real_run_target_identical_entry_sets(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    dry_out = tmp_path / "dry-out"
    assert main(_clean_args(root, plan_path, token_path, dry_out, plan_hash) + ["--dry-run"]) == 0
    dry_log = json.loads((dry_out / "clean_action_log.json").read_text(encoding="utf-8"))
    dry_set = {
        record["entry_id"]
        for record in dry_log["entries"]
        if record["decision"] == "DRY_RUN_WOULD_REMOVE"
    }

    real_out = tmp_path / "real-out"
    assert main(_clean_args(root, plan_path, token_path, real_out, plan_hash)) == 0
    real_log = json.loads((real_out / "clean_action_log.json").read_text(encoding="utf-8"))
    real_set = {
        record["entry_id"] for record in real_log["entries"] if record["decision"] == "REMOVED"
    }

    assert dry_set == real_set
    assert real_log["summary"]["partial"] is False


def test_partial_run_reported_when_entry_is_skipped(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    # Plant a protected name so one SAFE entry is skipped at execution time.
    (repo / "dist" / ".env").write_text("PLANTED=synthetic", encoding="utf-8")

    clean_out = tmp_path / "clean-out"
    exit_code = main(_clean_args(root, plan_path, token_path, clean_out, plan_hash))

    assert exit_code == 0
    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    assert log["summary"]["partial"] is True
    assert log["summary"]["proposed_total"] == 2
    assert log["summary"]["removed"] == 1

    report = (clean_out / "clean_report.md").read_text(encoding="utf-8")
    assert "STATUS: PARTIAL" in report
    assert "`demo/dist`" in report
    assert "SKIPPED_PROTECTED" in report


def test_clean_report_never_claims_rollback(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    clean_out = tmp_path / "clean-out"
    assert main(_clean_args(root, plan_path, token_path, clean_out, plan_hash)) == 0

    report = (clean_out / "clean_report.md").read_text(encoding="utf-8")
    assert "There is NO rollback." in report
    assert "rescan, replan, and reapprove" in report
    assert "STATUS: COMPLETE" in report


def test_dry_run_report_written_and_marked(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    dry_out = tmp_path / "dry-out"
    assert main(_clean_args(root, plan_path, token_path, dry_out, plan_hash) + ["--dry-run"]) == 0

    report = (dry_out / "clean_report.md").read_text(encoding="utf-8")
    assert "STATUS: DRY_RUN" in report
    assert "Dry run: YES" in report
    assert not (dry_out / "removed_manifest.json").exists()


def test_failed_removal_stops_run_and_reports_error(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    clean_out = tmp_path / "clean-out"
    # Hold an open handle inside the first proposed entry so removal fails on Windows.
    victim = repo / ".pytest_cache" / "x"
    with victim.open("r", encoding="utf-8"):
        exit_code = main(_clean_args(root, plan_path, token_path, clean_out, plan_hash))

    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    if log["summary"]["errors"] == 0:
        # POSIX platforms may allow unlinking open files; nothing to assert further.
        assert exit_code == 0
        return

    assert exit_code == 1
    assert log["failed"] is True
    assert log["summary"]["partial"] is True
    decisions = {record["entry_id"]: record["decision"] for record in log["entries"]}
    assert decisions["demo/.pytest_cache"] == "ERROR"
    assert decisions["demo/dist"] == "NOT_PROCESSED", "fail-fast must stop later entries"
    report = (clean_out / "clean_report.md").read_text(encoding="utf-8")
    assert "STATUS: PARTIAL" in report
