import json
from pathlib import Path

from repo_cleanroom.cli import main


def _run_sample_scan(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    out_dir = tmp_path / "reports"

    python_repo = root / "python-demo"
    (python_repo / ".git").mkdir(parents=True)
    (python_repo / "pyproject.toml").write_text("[project]\nname='python-demo'", encoding="utf-8")
    (python_repo / ".venv").mkdir()
    (python_repo / ".venv" / "marker.txt").write_text("venv", encoding="utf-8")
    (python_repo / ".env").write_text("DO_NOT_PRINT=1", encoding="utf-8")

    node_repo = root / "node-demo"
    (node_repo / ".git").mkdir(parents=True)
    (node_repo / "package.json").write_text('{"name":"node-demo"}', encoding="utf-8")
    (node_repo / "node_modules").mkdir()
    (node_repo / "node_modules" / "large.js").write_text("x" * 20, encoding="utf-8")

    exit_code = main(["scan", "--root", str(root), "--out-dir", str(out_dir)])
    assert exit_code == 0
    return out_dir


def test_scan_report_json_schema_contract(tmp_path: Path):
    out_dir = _run_sample_scan(tmp_path)

    schema = json.loads((out_dir / "schema_version.json").read_text(encoding="utf-8"))
    assert schema["schema_version"] == "0.1.0"
    assert schema["tool"] == "repo-cleanroom"
    assert schema["command"] == "scan"
    assert schema["mode"] == "READ_ONLY_SCAN"
    assert "generated_at_utc" in schema

    inventory = json.loads((out_dir / "inventory.json").read_text(encoding="utf-8"))
    assert inventory["schema_version"] == "0.1.0"
    assert inventory["status"] == "OK"
    assert inventory["mode"] == "READ_ONLY_SCAN"
    assert isinstance(inventory["repos"], list)
    assert isinstance(inventory["manifests"], list)
    assert inventory["totals"]["repos"] == 2
    assert inventory["safety"]["cleanup_performed"] is False
    assert inventory["safety"]["shell_history_read"] is False
    assert inventory["safety"]["target_repo_scripts_executed"] is False

    artifact_inventory = json.loads((out_dir / "artifact_inventory.json").read_text(encoding="utf-8"))
    assert artifact_inventory["schema_version"] == "0.1.0"
    assert artifact_inventory["status"] == "OK"
    assert artifact_inventory["mode"] == "READ_ONLY_SCAN"
    assert isinstance(artifact_inventory["artifacts"], list)
    assert artifact_inventory["totals"]["artifacts"] == 3
    assert "by_risk" in artifact_inventory["totals"]
    assert "by_type" in artifact_inventory["totals"]

    public_safety = json.loads((out_dir / "public_safety_check.json").read_text(encoding="utf-8"))
    assert public_safety["schema_version"] == "0.1.0"
    assert public_safety["status"] == "PASS"
    assert public_safety["external_side_effect"] is False
    assert public_safety["cleanup_performed"] is False
    assert isinstance(public_safety["notes"], list)


def test_artifact_records_keep_required_fields(tmp_path: Path):
    out_dir = _run_sample_scan(tmp_path)
    payload = json.loads((out_dir / "artifact_inventory.json").read_text(encoding="utf-8"))

    required = {
        "repo_path",
        "path",
        "relative_path",
        "artifact_type",
        "risk",
        "reason",
        "size_bytes",
        "file_count",
        "is_symlink",
        "scan_errors",
        "repo_name",
        "repo_relative_path",
    }

    assert payload["artifacts"]
    for item in payload["artifacts"]:
        assert required.issubset(item)
