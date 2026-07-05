import json
from pathlib import Path

from repo_cleanroom.cli import main

from test_clean_command import _clean_args, _make_workspace, _scan_plan_approve


def _verify_args(root: Path, plan: Path, log: Path, out_dir: Path) -> list[str]:
    return [
        "verify",
        "--root",
        str(root),
        "--plan",
        str(plan),
        "--action-log",
        str(log),
        "--out-dir",
        str(out_dir),
    ]


def _clean_workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    """scan -> plan -> approve -> clean. Returns (root, plan_path, action_log_path)."""

    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)
    clean_out = tmp_path / "clean-out"
    assert main(_clean_args(root, plan_path, token_path, clean_out, plan_hash)) == 0
    return root, plan_path, clean_out / "clean_action_log.json"


def test_verify_passes_after_faithful_clean(tmp_path: Path):
    root, plan_path, log_path = _clean_workspace(tmp_path)

    verify_out = tmp_path / "verify-out"
    exit_code = main(_verify_args(root, plan_path, log_path, verify_out))

    assert exit_code == 0
    payload = json.loads((verify_out / "verify.json").read_text(encoding="utf-8"))
    assert payload["summary"]["verified"] is True
    assert payload["summary"]["fail_still_present"] == 0
    assert payload["summary"]["fail_missing"] == 0
    removed = [e for e in payload["entries"] if e["log_decision"] == "REMOVED"]
    assert removed and all(e["expected"] == "ABSENT" and e["actual"] == "ABSENT" for e in removed)
    assert payload["inputs"]["plan"]["sha256"]
    assert payload["inputs"]["action_log"]["sha256"]


def test_verify_detects_remaining_target(tmp_path: Path):
    root, plan_path, log_path = _clean_workspace(tmp_path)

    # Recreate a removed artifact: verification must flag it as still present.
    (root / "demo" / "dist").mkdir()

    verify_out = tmp_path / "verify-out"
    exit_code = main(_verify_args(root, plan_path, log_path, verify_out))

    assert exit_code == 1
    payload = json.loads((verify_out / "verify.json").read_text(encoding="utf-8"))
    assert payload["summary"]["verified"] is False
    dist = [e for e in payload["entries"] if e["entry_id"] == "demo/dist"][0]
    assert dist["result"] == "FAIL_STILL_PRESENT"


def test_verify_detects_unexpectedly_missing_item(tmp_path: Path):
    root, plan_path, log_path = _clean_workspace(tmp_path)

    # Delete a BLOCKED item outside the tool: verification must flag the loss.
    (root / "demo" / ".env").unlink()

    verify_out = tmp_path / "verify-out"
    exit_code = main(_verify_args(root, plan_path, log_path, verify_out))

    assert exit_code == 1
    payload = json.loads((verify_out / "verify.json").read_text(encoding="utf-8"))
    env = [e for e in payload["entries"] if e["entry_id"] == "demo/.env"][0]
    assert env["result"] == "FAIL_MISSING"


def test_verify_rejects_mismatched_plan_and_log(tmp_path: Path):
    root, plan_path, log_path = _clean_workspace(tmp_path)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["plan_id"] = "00000000-0000-0000-0000-000000000000"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    exit_code = main(_verify_args(root, plan_path, log_path, tmp_path / "verify-out"))

    assert exit_code == 2


def test_verify_accepts_dry_run_log_with_everything_present(tmp_path: Path):
    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)
    dry_out = tmp_path / "dry-out"
    assert main(_clean_args(root, plan_path, token_path, dry_out, plan_hash) + ["--dry-run"]) == 0

    verify_out = tmp_path / "verify-out"
    exit_code = main(
        _verify_args(root, plan_path, dry_out / "clean_action_log.json", verify_out)
    )

    assert exit_code == 0
    payload = json.loads((verify_out / "verify.json").read_text(encoding="utf-8"))
    assert payload["action_log_dry_run"] is True
    assert payload["summary"]["verified"] is True
    assert all(e["expected"] == "PRESENT" for e in payload["entries"])


def test_verify_is_read_only(tmp_path: Path):
    root, plan_path, log_path = _clean_workspace(tmp_path)
    before = {str(item) for item in root.rglob("*")}

    assert main(_verify_args(root, plan_path, log_path, tmp_path / "verify-out")) == 0

    assert {str(item) for item in root.rglob("*")} == before
