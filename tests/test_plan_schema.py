"""Contract tests for the cleanup_plan.json schema (v0.2.2).

These tests pin the plan schema so it cannot drift silently, and validate the
committed synthetic sample against the same contract.
"""

import json
from pathlib import Path

from repo_cleanroom.cli import main

PLAN_TOP_LEVEL_FIELDS = {
    "plan_id",
    "plan_schema_version",
    "generated_at_utc",
    "mode",
    "root",
    "source_artifact_inventory",
    "entries",
    "summary",
    "plan_hash",
}

PLAN_ENTRY_FIELDS = {
    "entry_id",
    "repo_name",
    "repo_relative_path",
    "relative_path",
    "path",
    "artifact_type",
    "risk",
    "size_bytes",
    "file_count",
    "is_symlink",
    "proposed_action",
    "reason",
}

PLAN_SUMMARY_FIELDS = {
    "total_entries",
    "proposed_remove_count",
    "proposed_remove_bytes",
    "review_required_count",
    "blocked_count",
    "no_action_count",
    "by_risk",
}

SOURCE_INVENTORY_FIELDS = {"path", "schema_version", "sha256"}

ALLOWED_ACTIONS = {"PROPOSE_REMOVE", "REVIEW_REQUIRED", "FORBIDDEN", "NO_ACTION"}


def _assert_plan_contract(plan: dict) -> None:
    assert set(plan.keys()) == PLAN_TOP_LEVEL_FIELDS
    assert plan["mode"] == "PLAN_ONLY"
    assert plan["plan_schema_version"] == "0.2.0"
    assert set(plan["source_artifact_inventory"].keys()) == SOURCE_INVENTORY_FIELDS
    assert set(plan["summary"].keys()) == PLAN_SUMMARY_FIELDS

    for entry in plan["entries"]:
        assert set(entry.keys()) == PLAN_ENTRY_FIELDS
        assert entry["proposed_action"] in ALLOWED_ACTIONS

    summary = plan["summary"]
    assert summary["total_entries"] == len(plan["entries"])
    action_counts = {
        "PROPOSE_REMOVE": summary["proposed_remove_count"],
        "REVIEW_REQUIRED": summary["review_required_count"],
        "FORBIDDEN": summary["blocked_count"],
        "NO_ACTION": summary["no_action_count"],
    }
    for action, expected in action_counts.items():
        actual = sum(1 for entry in plan["entries"] if entry["proposed_action"] == action)
        assert actual == expected, f"summary count mismatch for {action}"
    assert summary["proposed_remove_bytes"] == sum(
        entry["size_bytes"]
        for entry in plan["entries"]
        if entry["proposed_action"] == "PROPOSE_REMOVE"
    )


def test_generated_plan_matches_contract(tmp_path: Path):
    root = tmp_path / "workspace"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    (repo / ".pytest_cache").mkdir()
    (repo / ".pytest_cache" / "x").write_text("cache", encoding="utf-8")
    (repo / ".env").write_text("PLACEHOLDER=synthetic", encoding="utf-8")

    scan_out = tmp_path / "scan-reports"
    plan_out = tmp_path / "plan-reports"
    assert main(["scan", "--root", str(root), "--out-dir", str(scan_out)]) == 0
    assert (
        main(
            [
                "plan",
                "--scan-artifacts",
                str(scan_out / "artifact_inventory.json"),
                "--out-dir",
                str(plan_out),
            ]
        )
        == 0
    )

    plan = json.loads((plan_out / "cleanup_plan.json").read_text(encoding="utf-8"))
    _assert_plan_contract(plan)
    assert plan["plan_hash"] is None


def test_sample_plan_matches_contract():
    sample_path = Path(__file__).parent.parent / "examples" / "sample-plan" / "cleanup_plan.json"
    plan = json.loads(sample_path.read_text(encoding="utf-8"))
    _assert_plan_contract(plan)


def test_sample_plan_has_no_executable_semantics():
    sample_path = Path(__file__).parent.parent / "examples" / "sample-plan" / "cleanup_plan.json"
    plan = json.loads(sample_path.read_text(encoding="utf-8"))

    assert plan["mode"] == "PLAN_ONLY"
    blocked = [entry for entry in plan["entries"] if entry["risk"] == "BLOCKED"]
    assert blocked, "sample must demonstrate a BLOCKED item"
    assert all(entry["proposed_action"] == "FORBIDDEN" for entry in blocked)
