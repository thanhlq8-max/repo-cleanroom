from pathlib import Path

from repo_cleanroom.cli import build_scan_payload
from repo_cleanroom.scanner.repo_discovery import discover_repositories


def test_discover_repositories(tmp_path: Path):
    repo = tmp_path / "demo"
    (repo / ".git").mkdir(parents=True)

    records = discover_repositories(tmp_path)

    assert len(records) == 1
    assert records[0].name == "demo"
    assert records[0].relative_path == "demo"


def test_build_scan_payload_reports_artifact(tmp_path: Path):
    repo = tmp_path / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "package.json").write_text("{}", encoding="utf-8")
    node_modules = repo / "node_modules"
    node_modules.mkdir()
    (node_modules / "left-pad.txt").write_text("x", encoding="utf-8")

    inventory, artifact_inventory, public_safety = build_scan_payload(tmp_path)

    assert inventory["totals"]["repos"] == 1
    assert inventory["totals"]["manifests"] == 1
    assert artifact_inventory["totals"]["artifacts"] == 1
    assert artifact_inventory["artifacts"][0]["risk"] == "SAFE"
    assert public_safety["status"] == "PASS"
