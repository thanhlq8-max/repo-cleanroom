import json
from pathlib import Path

from repo_cleanroom.cli import main

from test_clean_command import _clean_args, _make_workspace, _scan_plan_approve
from test_verify_command import _verify_args


def _attest_args(plan: Path, log: Path, verify: Path, out_dir: Path) -> list[str]:
    return [
        "attest",
        "--plan",
        str(plan),
        "--action-log",
        str(log),
        "--verify",
        str(verify),
        "--out-dir",
        str(out_dir),
    ]


def _full_pipeline(tmp_path: Path, plant_secret: bool = False) -> tuple[Path, Path, Path, Path]:
    """scan -> plan -> approve -> clean -> verify.

    Returns (root, plan_path, action_log_path, verify_path).
    """

    root = _make_workspace(tmp_path)
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)
    if plant_secret:
        (root / "demo" / "dist" / ".env").write_text("PLANTED=synthetic", encoding="utf-8")
    clean_out = tmp_path / "clean-out"
    assert main(_clean_args(root, plan_path, token_path, clean_out, plan_hash)) == 0
    log_path = clean_out / "clean_action_log.json"
    verify_out = tmp_path / "verify-out"
    exit_code = main(_verify_args(root, plan_path, log_path, verify_out))
    assert exit_code == 0
    return root, plan_path, log_path, verify_out / "verify.json"


def test_attestation_separates_all_categories(tmp_path: Path):
    _, plan_path, log_path, verify_path = _full_pipeline(tmp_path)

    attest_out = tmp_path / "attest-out"
    exit_code = main(_attest_args(plan_path, log_path, verify_path, attest_out))

    assert exit_code == 0
    attestation = json.loads((attest_out / "attestation.json").read_text(encoding="utf-8"))
    assert attestation["status"] == "ATTESTED"
    assert attestation["counts"]["cleaned"] == 2
    assert attestation["counts"]["blocked"] == 1
    assert attestation["counts"]["failed"] == 0
    cleaned_ids = {item["entry_id"] for item in attestation["categories"]["cleaned"]}
    assert cleaned_ids == {"demo/.pytest_cache", "demo/dist"}
    blocked_ids = {item["entry_id"] for item in attestation["categories"]["blocked"]}
    assert blocked_ids == {"demo/.env"}
    for key in ("plan", "action_log", "verify"):
        assert attestation["inputs"][key]["sha256"]


def test_attestation_reports_skipped_entries(tmp_path: Path):
    _, plan_path, log_path, verify_path = _full_pipeline(tmp_path, plant_secret=True)

    attest_out = tmp_path / "attest-out"
    exit_code = main(_attest_args(plan_path, log_path, verify_path, attest_out))

    assert exit_code == 0
    attestation = json.loads((attest_out / "attestation.json").read_text(encoding="utf-8"))
    skipped_ids = {item["entry_id"] for item in attestation["categories"]["skipped"]}
    assert "demo/dist" in skipped_ids
    assert attestation["counts"]["cleaned"] == 1

    report = (attest_out / "final_report.md").read_text(encoding="utf-8")
    assert "Skipped (guards or fail-fast; still on disk)" in report
    assert "`demo/dist`" in report


def test_attestation_refuses_when_verification_failed(tmp_path: Path):
    root, plan_path, log_path, verify_path = _full_pipeline(tmp_path)

    # Invalidate the verified state: recreate a removed artifact, re-verify.
    (root / "demo" / "dist").mkdir()
    verify_out2 = tmp_path / "verify-out-2"
    assert main(_verify_args(root, plan_path, log_path, verify_out2)) == 1

    attest_out = tmp_path / "attest-out"
    exit_code = main(
        _attest_args(plan_path, log_path, verify_out2 / "verify.json", attest_out)
    )

    assert exit_code == 1
    attestation = json.loads((attest_out / "attestation.json").read_text(encoding="utf-8"))
    assert attestation["status"] == "NOT_ATTESTED_VERIFICATION_FAILED"
    report = (attest_out / "final_report.md").read_text(encoding="utf-8")
    assert "VERIFICATION FAILED" in report


def test_final_report_limits_its_claims(tmp_path: Path):
    _, plan_path, log_path, verify_path = _full_pipeline(tmp_path)

    attest_out = tmp_path / "attest-out"
    assert main(_attest_args(plan_path, log_path, verify_path, attest_out)) == 0

    report = (attest_out / "final_report.md").read_text(encoding="utf-8")
    assert "covers only the entries of the plan named above" in report
    assert "no claim about any other file" in report
    assert "There is NO rollback" in report


def test_attestation_rejects_mismatched_inputs(tmp_path: Path):
    _, plan_path, log_path, verify_path = _full_pipeline(tmp_path)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["plan_id"] = "00000000-0000-0000-0000-000000000000"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    exit_code = main(_attest_args(plan_path, log_path, verify_path, tmp_path / "attest-out"))

    assert exit_code == 2
