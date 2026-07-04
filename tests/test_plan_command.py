import json
from pathlib import Path

from repo_cleanroom.cli import main


def _snapshot(root: Path) -> set[str]:
    return {str(item) for item in root.rglob("*")}


def _run_scan_then_plan(tmp_path: Path) -> tuple[Path, Path, dict]:
    root = tmp_path / "workspace"
    scan_out = tmp_path / "scan-reports"
    plan_out = tmp_path / "plan-reports"

    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    (repo / ".pytest_cache").mkdir()
    (repo / ".pytest_cache" / "x").write_text("cache", encoding="utf-8")
    (repo / ".env").write_text("PLACEHOLDER=synthetic", encoding="utf-8")

    assert main(["scan", "--root", str(root), "--out-dir", str(scan_out)]) == 0

    exit_code = main(
        [
            "plan",
            "--scan-artifacts",
            str(scan_out / "artifact_inventory.json"),
            "--out-dir",
            str(plan_out),
        ]
    )
    assert exit_code == 0

    plan = json.loads((plan_out / "cleanup_plan.json").read_text(encoding="utf-8"))
    return root, plan_out, plan


def test_plan_command_writes_plan_files_and_removes_nothing(tmp_path: Path):
    root = tmp_path / "workspace"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    (repo / ".pytest_cache").mkdir()
    (repo / ".pytest_cache" / "x").write_text("cache", encoding="utf-8")
    (repo / ".env").write_text("PLACEHOLDER=synthetic", encoding="utf-8")

    scan_out = tmp_path / "scan-reports"
    assert main(["scan", "--root", str(root), "--out-dir", str(scan_out)]) == 0

    before = _snapshot(root)

    plan_out = tmp_path / "plan-reports"
    exit_code = main(
        [
            "plan",
            "--scan-artifacts",
            str(scan_out / "artifact_inventory.json"),
            "--out-dir",
            str(plan_out),
        ]
    )

    assert exit_code == 0
    assert (plan_out / "cleanup_plan.json").exists()
    assert (plan_out / "cleanup_plan.md").exists()
    # The core v0.2.x contract: plan generation removes nothing from the workspace.
    assert _snapshot(root) == before
    assert (repo / ".pytest_cache" / "x").read_text(encoding="utf-8") == "cache"


def test_plan_payload_follows_action_mapping(tmp_path: Path):
    _, _, plan = _run_scan_then_plan(tmp_path)

    assert plan["mode"] == "PLAN_ONLY"
    assert plan["plan_schema_version"] == "0.2.0"
    assert plan["plan_hash"] is None

    actions = {entry["entry_id"]: entry["proposed_action"] for entry in plan["entries"]}
    assert actions["demo/.pytest_cache"] == "PROPOSE_REMOVE"
    assert actions["demo/.env"] == "FORBIDDEN"

    summary = plan["summary"]
    assert summary["total_entries"] == len(plan["entries"])
    assert summary["proposed_remove_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["proposed_remove_bytes"] == sum(
        entry["size_bytes"]
        for entry in plan["entries"]
        if entry["proposed_action"] == "PROPOSE_REMOVE"
    )


def test_plan_records_source_inventory_provenance(tmp_path: Path):
    _, _, plan = _run_scan_then_plan(tmp_path)

    provenance = plan["source_artifact_inventory"]
    assert provenance["path"].endswith("artifact_inventory.json")
    assert provenance["schema_version"] == "0.1.0"
    assert len(provenance["sha256"]) == 64


def test_plan_fails_when_artifact_escapes_root(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside-artifact"
    outside.mkdir()

    inventory = {
        "schema_version": "0.1.0",
        "root": str(root),
        "artifacts": [
            {
                "repo_name": "demo",
                "repo_relative_path": "demo",
                "relative_path": "node_modules",
                "path": str(outside),
                "artifact_type": "node_dependencies",
                "risk": "SAFE",
                "size_bytes": 10,
                "file_count": 1,
                "is_symlink": False,
            }
        ],
    }
    inventory_path = tmp_path / "artifact_inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    plan_out = tmp_path / "plan-reports"
    exit_code = main(
        ["plan", "--scan-artifacts", str(inventory_path), "--out-dir", str(plan_out)]
    )

    assert exit_code == 2
    # No partial plan may be written when any entry fails the path guard.
    assert not (plan_out / "cleanup_plan.json").exists()
    assert not (plan_out / "cleanup_plan.md").exists()


def test_plan_fails_on_unknown_risk(tmp_path: Path):
    root = tmp_path / "workspace"
    (root / "demo" / "dist").mkdir(parents=True)

    inventory = {
        "schema_version": "0.1.0",
        "root": str(root),
        "artifacts": [
            {
                "repo_name": "demo",
                "repo_relative_path": "demo",
                "relative_path": "dist",
                "path": str(root / "demo" / "dist"),
                "artifact_type": "build_output",
                "risk": "TOTALLY_FINE",
                "size_bytes": 10,
                "file_count": 1,
                "is_symlink": False,
            }
        ],
    }
    inventory_path = tmp_path / "artifact_inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    exit_code = main(
        ["plan", "--scan-artifacts", str(inventory_path), "--out-dir", str(tmp_path / "out")]
    )

    assert exit_code == 2


def test_plan_marks_safe_symlink_as_no_action(tmp_path: Path):
    root = tmp_path / "workspace"
    (root / "demo" / "node_modules").mkdir(parents=True)

    inventory = {
        "schema_version": "0.1.0",
        "root": str(root),
        "artifacts": [
            {
                "repo_name": "demo",
                "repo_relative_path": "demo",
                "relative_path": "node_modules",
                "path": str(root / "demo" / "node_modules"),
                "artifact_type": "node_dependencies",
                "risk": "SAFE",
                "size_bytes": 10,
                "file_count": 1,
                "is_symlink": True,
            }
        ],
    }
    inventory_path = tmp_path / "artifact_inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    plan_out = tmp_path / "plan-reports"
    exit_code = main(
        ["plan", "--scan-artifacts", str(inventory_path), "--out-dir", str(plan_out)]
    )

    assert exit_code == 0
    plan = json.loads((plan_out / "cleanup_plan.json").read_text(encoding="utf-8"))
    assert plan["entries"][0]["proposed_action"] == "NO_ACTION"
    assert plan["summary"]["proposed_remove_count"] == 0


def test_plan_requires_scan_artifacts_argument(tmp_path: Path):
    try:
        main(["plan", "--out-dir", str(tmp_path / "out")])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for missing required --scan-artifacts")
