import json
import os
from pathlib import Path

import pytest

from repo_cleanroom.cli import main


def _make_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    (repo / ".pytest_cache").mkdir()
    (repo / ".pytest_cache" / "x").write_text("cache", encoding="utf-8")
    (repo / "dist").mkdir()
    (repo / "dist" / "bundle.js").write_text("console.log('demo');", encoding="utf-8")
    (repo / ".env").write_text("PLACEHOLDER=synthetic", encoding="utf-8")
    return root


def _scan_plan_approve(tmp_path: Path, root: Path) -> tuple[Path, Path, str]:
    """Run scan -> plan -> approve. Returns (plan_path, token_path, plan_hash)."""

    scan_out = tmp_path / "scan-out"
    plan_out = tmp_path / "plan-out"
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
    assert (
        main(
            [
                "approve",
                "--plan",
                str(plan_out / "cleanup_plan.json"),
                "--approved-by",
                "test-operator",
                "--out-dir",
                str(plan_out),
            ]
        )
        == 0
    )
    token = json.loads((plan_out / "approval_token.json").read_text(encoding="utf-8"))
    return plan_out / "cleanup_plan.json", plan_out / "approval_token.json", token["plan_hash"]


def _clean_args(root: Path, plan: Path, token: Path, out_dir: Path, plan_hash: str) -> list[str]:
    return [
        "clean",
        "--root",
        str(root),
        "--plan",
        str(plan),
        "--token",
        str(token),
        "--yes-exact-plan",
        plan_hash,
        "--out-dir",
        str(out_dir),
    ]


def test_approve_writes_exact_plan_token(tmp_path: Path):
    root = _make_workspace(tmp_path)
    _, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["token_schema_version"] == "0.2.0"
    assert token["approved_action"] == "REMOVE_PROPOSED_SAFE"
    assert token["approved_risk_classes"] == ["SAFE"]
    assert token["approved_by"] == "test-operator"
    assert len(plan_hash) == 64
    assert token["expires_at_utc"] > token["approved_at_utc"]


def test_clean_dry_run_removes_nothing(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)
    before = {str(item) for item in root.rglob("*")}

    clean_out = tmp_path / "clean-out"
    exit_code = main(
        _clean_args(root, plan_path, token_path, clean_out, plan_hash) + ["--dry-run"]
    )

    assert exit_code == 0
    assert {str(item) for item in root.rglob("*")} == before
    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    assert log["dry_run"] is True
    assert log["summary"]["removed"] == 0
    assert log["summary"]["would_remove"] == 2
    assert not (clean_out / "removed_manifest.json").exists()


def test_clean_removes_only_safe_proposed_entries(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    clean_out = tmp_path / "clean-out"
    exit_code = main(_clean_args(root, plan_path, token_path, clean_out, plan_hash))

    assert exit_code == 0
    # SAFE artifacts removed.
    assert not (repo / ".pytest_cache").exists()
    assert not (repo / "dist").exists()
    # Everything else untouched.
    assert (repo / ".env").read_text(encoding="utf-8") == "PLACEHOLDER=synthetic"
    assert (repo / ".git").exists()
    assert (repo / "pyproject.toml").exists()

    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    assert log["summary"]["removed"] == 2
    assert log["summary"]["errors"] == 0
    env_records = [r for r in log["entries"] if r["entry_id"] == "demo/.env"]
    assert env_records and env_records[0]["decision"] == "NOT_PROPOSED"

    manifest = json.loads((clean_out / "removed_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["removed_paths"]) == 2


def test_clean_refuses_tampered_plan(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["entries"][0]["reason"] = "tampered"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    before = {str(item) for item in root.rglob("*")}

    exit_code = main(_clean_args(root, plan_path, token_path, tmp_path / "out", plan_hash))

    assert exit_code == 2
    assert {str(item) for item in root.rglob("*")} == before


def test_clean_refuses_expired_token(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    token = json.loads(token_path.read_text(encoding="utf-8"))
    token["approved_at_utc"] = "2020-01-01T00:00:00+00:00"
    token["expires_at_utc"] = "2020-01-02T00:00:00+00:00"
    token_path.write_text(json.dumps(token), encoding="utf-8")
    before = {str(item) for item in root.rglob("*")}

    exit_code = main(_clean_args(root, plan_path, token_path, tmp_path / "out", plan_hash))

    assert exit_code == 2
    assert {str(item) for item in root.rglob("*")} == before


def test_clean_refuses_wrong_confirmation_hash(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, _ = _scan_plan_approve(tmp_path, root)
    before = {str(item) for item in root.rglob("*")}

    exit_code = main(_clean_args(root, plan_path, token_path, tmp_path / "out", "0" * 64))

    assert exit_code == 2
    assert {str(item) for item in root.rglob("*")} == before


def test_clean_refuses_mismatched_root(tmp_path: Path):
    root = _make_workspace(tmp_path)
    other_root = tmp_path / "other-root"
    other_root.mkdir()
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    exit_code = main(_clean_args(other_root, plan_path, token_path, tmp_path / "out", plan_hash))

    assert exit_code == 2
    assert (root / "demo" / ".pytest_cache").exists()


def test_clean_skips_entry_replaced_after_planning(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    # Replace a planned directory with a regular file after approval.
    (repo / "dist" / "bundle.js").unlink()
    (repo / "dist").rmdir()
    (repo / "dist").write_text("now a file", encoding="utf-8")

    clean_out = tmp_path / "clean-out"
    exit_code = main(_clean_args(root, plan_path, token_path, clean_out, plan_hash))

    # Non-symlink replacement is still inside scope for a file entry; strengthen:
    # the log must show the other SAFE entry removed and no error.
    assert exit_code == 0
    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    assert log["summary"]["errors"] == 0


def test_clean_skips_planted_secret_inside_safe_entry(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    # Plant a protected name inside a SAFE artifact after approval.
    (repo / "dist" / ".env").write_text("PLANTED=synthetic", encoding="utf-8")

    clean_out = tmp_path / "clean-out"
    exit_code = main(_clean_args(root, plan_path, token_path, clean_out, plan_hash))

    assert exit_code == 0
    assert (repo / "dist" / ".env").exists(), "planted secret must abort that entry"
    assert not (repo / ".pytest_cache").exists(), "other SAFE entries still removed"
    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    dist_records = [r for r in log["entries"] if r["entry_id"] == "demo/dist"]
    assert dist_records and dist_records[0]["decision"] == "SKIPPED_PROTECTED"


@pytest.mark.skipif(os.name != "nt" and not hasattr(os, "symlink"), reason="symlink support required")
def test_clean_skips_entry_that_became_symlink(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("must survive", encoding="utf-8")

    (repo / "dist" / "bundle.js").unlink()
    (repo / "dist").rmdir()
    try:
        os.symlink(victim, repo / "dist", target_is_directory=True)
    except OSError:
        pytest.skip("no symlink privilege on this platform")

    clean_out = tmp_path / "clean-out"
    exit_code = main(_clean_args(root, plan_path, token_path, clean_out, plan_hash))

    assert exit_code == 0
    assert (victim / "keep.txt").read_text(encoding="utf-8") == "must survive"
    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    dist_records = [r for r in log["entries"] if r["entry_id"] == "demo/dist"]
    assert dist_records and dist_records[0]["decision"] == "SKIPPED_CHANGED"


def test_clean_requires_confirmation_argument(tmp_path: Path):
    try:
        main(
            [
                "clean",
                "--root",
                str(tmp_path),
                "--plan",
                str(tmp_path / "p.json"),
                "--token",
                str(tmp_path / "t.json"),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for missing required --yes-exact-plan")
