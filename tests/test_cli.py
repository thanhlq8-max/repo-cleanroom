import json
from pathlib import Path

from repo_cleanroom.cli import main


def test_cli_scan_writes_reports(tmp_path: Path):
    root = tmp_path / "workspace"
    out_dir = tmp_path / "reports"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    (repo / ".pytest_cache").mkdir()
    (repo / ".pytest_cache" / "x").write_text("cache", encoding="utf-8")

    exit_code = main(["scan", "--root", str(root), "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "inventory.json").exists()
    assert (out_dir / "artifact_inventory.json").exists()
    assert (out_dir / "findings.md").exists()

    artifact_payload = json.loads((out_dir / "artifact_inventory.json").read_text(encoding="utf-8"))
    assert artifact_payload["totals"]["artifacts"] == 1
    assert artifact_payload["artifacts"][0]["risk"] == "SAFE"


def test_cli_scan_requires_out_dir(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()

    try:
        main(["scan", "--root", str(root)])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for missing required --out-dir")
