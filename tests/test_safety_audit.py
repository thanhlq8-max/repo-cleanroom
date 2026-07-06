"""Safety audit regression tests (v0.9.1).

Covers the malicious-repo threat model in docs/THREAT_MODEL.md:
- Windows junctions must behave like symlinks at every boundary decision
  (scan size estimation, artifact flagging, clean-time guards);
- hostile file names must never break the scan or escape the root;
- secret file content must never appear in any output file.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from repo_cleanroom.cli import main
from repo_cleanroom.safety.symlink_guard import inspect_symlink, is_link_like
from repo_cleanroom.scanner.artifact_detector import detect_artifacts
from repo_cleanroom.scanner.size_indexer import estimate_path_size

IS_WINDOWS = os.name == "nt"


def _make_junction(target: Path, link: Path) -> None:
    """Create an NTFS junction or skip the test when unsupported."""

    if not IS_WINDOWS:
        pytest.skip("junctions exist only on Windows")
    try:
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
    except (ImportError, AttributeError, OSError) as exc:  # pragma: no cover
        pytest.skip(f"cannot create junction: {exc}")


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
                "safety-audit",
                "--out-dir",
                str(plan_out),
            ]
        )
        == 0
    )
    token = json.loads((plan_out / "approval_token.json").read_text(encoding="utf-8"))
    return plan_out / "cleanup_plan.json", plan_out / "approval_token.json", token["plan_hash"]


@pytest.mark.skipif(not IS_WINDOWS, reason="junctions exist only on Windows")
def test_size_indexer_does_not_traverse_junction(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"x" * 10_000)

    artifact = tmp_path / "workspace" / "repo" / "node_modules"
    artifact.mkdir(parents=True)
    (artifact / "inside.txt").write_bytes(b"y" * 100)
    _make_junction(outside, artifact / "escape")

    size_bytes, file_count, errors = estimate_path_size(artifact)

    assert size_bytes == 100, "junction target content must not be counted"
    assert file_count == 1
    assert any(err.startswith("SYMLINK_DIR_SKIPPED") for err in errors)


@pytest.mark.skipif(not IS_WINDOWS, reason="junctions exist only on Windows")
def test_inspect_symlink_flags_junction_like_symlink(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "workspace"
    root.mkdir()
    junction = root / "jlink"
    _make_junction(outside, junction)

    assert is_link_like(junction)
    finding = inspect_symlink(root, junction)
    assert finding.is_symlink is True
    assert finding.target_inside_root is False


@pytest.mark.skipif(not IS_WINDOWS, reason="junctions exist only on Windows")
def test_scan_marks_junction_artifact_as_symlink(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"x" * 10_000)

    root = tmp_path / "workspace"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    _make_junction(outside, repo / "node_modules")

    records = detect_artifacts(repo, root=root)

    node = [r for r in records if r.relative_path == "node_modules"]
    assert node, "junction artifact must still be detected"
    assert node[0].is_symlink is True
    assert node[0].size_bytes == 0, "junction target must not contribute size"
    assert "SYMLINK_NOT_TRAVERSED" in node[0].scan_errors


@pytest.mark.skipif(not IS_WINDOWS, reason="junctions exist only on Windows")
def test_clean_refuses_junction_planted_inside_safe_entry(tmp_path: Path):
    """A junction planted into an approved SAFE entry must abort that entry.

    Regression for the audit finding: os.walk(followlinks=False) descends into
    junctions, so without the reparse guard the clean step would delete files
    outside the root through the junction.
    """

    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("must survive", encoding="utf-8")
    _make_junction(victim, repo / "dist" / "escape")

    clean_out = tmp_path / "clean-out"
    exit_code = main(
        [
            "clean",
            "--root",
            str(root),
            "--plan",
            str(plan_path),
            "--token",
            str(token_path),
            "--yes-exact-plan",
            plan_hash,
            "--out-dir",
            str(clean_out),
        ]
    )

    assert exit_code == 0
    assert (victim / "keep.txt").read_text(encoding="utf-8") == "must survive"
    assert (repo / "dist" / "bundle.js").exists(), "refused entry must stay intact"
    assert not (repo / ".pytest_cache").exists(), "unaffected SAFE entries still removed"

    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    dist_records = [r for r in log["entries"] if r["entry_id"] == "demo/dist"]
    assert dist_records and dist_records[0]["decision"] == "SKIPPED_GUARD_FAIL"
    assert "reparse" in dist_records[0]["reason"]


@pytest.mark.skipif(not IS_WINDOWS, reason="junctions exist only on Windows")
def test_clean_skips_entry_that_became_junction(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("must survive", encoding="utf-8")

    (repo / "dist" / "bundle.js").unlink()
    (repo / "dist").rmdir()
    _make_junction(victim, repo / "dist")

    clean_out = tmp_path / "clean-out"
    exit_code = main(
        [
            "clean",
            "--root",
            str(root),
            "--plan",
            str(plan_path),
            "--token",
            str(token_path),
            "--yes-exact-plan",
            plan_hash,
            "--out-dir",
            str(clean_out),
        ]
    )

    assert exit_code == 0
    assert (victim / "keep.txt").read_text(encoding="utf-8") == "must survive"
    log = json.loads((clean_out / "clean_action_log.json").read_text(encoding="utf-8"))
    dist_records = [r for r in log["entries"] if r["entry_id"] == "demo/dist"]
    assert dist_records and dist_records[0]["decision"] == "SKIPPED_CHANGED"


def test_scan_survives_hostile_artifact_content_names(tmp_path: Path):
    """Hostile names inside artifacts must not break the scan or leak outside root."""

    root = tmp_path / "workspace"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    dist = repo / "dist"
    dist.mkdir()

    hostile_names = [
        "unicode-üńï-….txt",
        "double  spaced  name.js",
        "$(synthetic-subshell).txt",
        "%TEMP%.txt",
        "semi;colon;name.txt",
        "quote'and“quote.txt",
    ]
    for name in hostile_names:
        (dist / name).write_text("synthetic", encoding="utf-8")

    out_dir = tmp_path / "out"
    assert main(["scan", "--root", str(root), "--out-dir", str(out_dir)]) == 0

    inventory = json.loads((out_dir / "artifact_inventory.json").read_text(encoding="utf-8"))
    dist_records = [a for a in inventory["artifacts"] if a["relative_path"] == "dist"]
    assert dist_records
    assert dist_records[0]["file_count"] == len(hostile_names)


def test_scan_outputs_never_contain_secret_content(tmp_path: Path):
    """The scan classifies secret files by name only; content must never leak."""

    marker = "SYNTHETIC_SECRET_MARKER_9f8e7d6c"
    root = tmp_path / "workspace"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".env").write_text(f"API_VALUE={marker}\n", encoding="utf-8")
    (repo / "dist").mkdir()
    (repo / "dist" / "app.js").write_text("console.log('demo');", encoding="utf-8")

    out_dir = tmp_path / "out"
    assert main(["scan", "--root", str(root), "--out-dir", str(out_dir)]) == 0

    for output_file in out_dir.rglob("*"):
        if output_file.is_file():
            content = output_file.read_text(encoding="utf-8", errors="replace")
            assert marker not in content, f"secret content leaked into {output_file.name}"


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX symlink counterpart of the junction tests"
)
def test_clean_refuses_symlink_planted_inside_safe_entry_posix(tmp_path: Path):
    root = _make_workspace(tmp_path)
    repo = root / "demo"
    plan_path, token_path, plan_hash = _scan_plan_approve(tmp_path, root)

    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("must survive", encoding="utf-8")
    os.symlink(victim, repo / "dist" / "escape", target_is_directory=True)

    clean_out = tmp_path / "clean-out"
    exit_code = main(
        [
            "clean",
            "--root",
            str(root),
            "--plan",
            str(plan_path),
            "--token",
            str(token_path),
            "--yes-exact-plan",
            plan_hash,
            "--out-dir",
            str(clean_out),
        ]
    )

    assert exit_code == 0
    assert (victim / "keep.txt").read_text(encoding="utf-8") == "must survive"
