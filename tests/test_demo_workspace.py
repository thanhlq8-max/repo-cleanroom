import json
from pathlib import Path

from repo_cleanroom.cli import main


def test_demo_workspace_creates_expected_shapes(tmp_path: Path):
    out_dir = tmp_path / "demo"

    exit_code = main(["demo-workspace", "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "demo-web-app" / ".git").is_dir()
    assert (out_dir / "demo-web-app" / "node_modules" / "left-pad" / "index.js").is_file()
    assert (out_dir / "demo-py-tool" / ".venv" / "Lib" / "site.py").is_file()
    assert (out_dir / "demo-rust-cli" / "target" / "debug" / "demo-rust-cli.d").is_file()


def test_demo_workspace_env_is_placeholder_only(tmp_path: Path):
    out_dir = tmp_path / "demo"
    assert main(["demo-workspace", "--out-dir", str(out_dir)]) == 0

    env_content = (out_dir / "demo-web-app" / ".env").read_text(encoding="utf-8")
    assert "PLACEHOLDER" in env_content
    assert "synthetic" in env_content


def test_demo_workspace_refuses_non_empty_target(tmp_path: Path):
    out_dir = tmp_path / "demo"
    out_dir.mkdir()
    (out_dir / "precious.txt").write_text("user data", encoding="utf-8")

    exit_code = main(["demo-workspace", "--out-dir", str(out_dir)])

    assert exit_code == 2
    assert (out_dir / "precious.txt").read_text(encoding="utf-8") == "user data"
    assert not (out_dir / "demo-web-app").exists()


def test_demo_workspace_scales_with_repo_count(tmp_path: Path):
    out_dir = tmp_path / "demo"

    exit_code = main(["demo-workspace", "--out-dir", str(out_dir), "--repo-count", "5"])

    assert exit_code == 0
    assert (out_dir / "demo-py-tool-0003" / ".git").is_dir()
    assert (out_dir / "demo-py-tool-0004" / "__pycache__").is_dir()


def test_demo_workspace_end_to_end_scan_and_plan(tmp_path: Path):
    out_dir = tmp_path / "demo"
    reports = tmp_path / "reports"
    assert main(["demo-workspace", "--out-dir", str(out_dir)]) == 0

    assert main(["scan", "--root", str(out_dir), "--out-dir", str(reports)]) == 0
    inventory = json.loads((reports / "artifact_inventory.json").read_text(encoding="utf-8"))
    assert inventory["totals"]["artifacts"] >= 6
    assert inventory["totals"]["by_risk"].get("BLOCKED", 0) >= 1

    assert (
        main(
            [
                "plan",
                "--scan-artifacts",
                str(reports / "artifact_inventory.json"),
                "--out-dir",
                str(reports),
            ]
        )
        == 0
    )
    plan = json.loads((reports / "cleanup_plan.json").read_text(encoding="utf-8"))
    assert plan["summary"]["proposed_remove_count"] >= 4
