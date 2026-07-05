import json
from pathlib import Path

from repo_cleanroom.cli import main
from repo_cleanroom.reports.html_report import render_findings_html


def _payloads() -> tuple[dict, dict]:
    inventory = {
        "root": "C:/demo/workspace",
        "repos": [{"name": "app", "relative_path": "app", "path": "C:/demo/workspace/app"}],
        "manifests": [],
    }
    artifact_inventory = {
        "artifacts": [
            {
                "risk": "SAFE",
                "artifact_type": "node_dependencies",
                "size_bytes": 2048,
                "repo_relative_path": "app",
                "relative_path": "node_modules",
                "reason": "common repo-local generated artifact",
            },
            {
                "risk": "BLOCKED",
                "artifact_type": "protected_config",
                "size_bytes": 42,
                "repo_relative_path": "app",
                "relative_path": ".env",
                "reason": "protected sensitive path/name pattern",
            },
        ]
    }
    return inventory, artifact_inventory


def test_html_report_is_self_contained_and_grouped():
    inventory, artifact_inventory = _payloads()

    html = render_findings_html(inventory, artifact_inventory)

    assert html.startswith("<!DOCTYPE html>")
    assert "<script" not in html.lower()
    assert "http://" not in html and "https://" not in html  # no external resources
    assert "badge-SAFE" in html and "badge-BLOCKED" in html
    assert "app/node_modules" in html
    assert "READ_ONLY_SCAN_COMPLETE" in html


def test_html_report_escapes_untrusted_names():
    inventory, artifact_inventory = _payloads()
    artifact_inventory["artifacts"][0]["relative_path"] = '<script>alert("x")</script>'
    artifact_inventory["artifacts"][0]["reason"] = "<img src=x onerror=alert(1)>"
    inventory["repos"][0]["name"] = "<b>bold-repo</b>"

    html = render_findings_html(inventory, artifact_inventory)

    assert "<script>alert" not in html
    assert "<img" not in html
    assert "<b>bold-repo</b>" not in html
    assert "&lt;script&gt;" in html


def test_cli_html_report_writes_file_only_into_out_dir(tmp_path: Path):
    inventory, artifact_inventory = _payloads()
    inventory_path = tmp_path / "inventory.json"
    artifacts_path = tmp_path / "artifact_inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    artifacts_path.write_text(json.dumps(artifact_inventory), encoding="utf-8")

    out_dir = tmp_path / "out"
    before = {str(item) for item in tmp_path.rglob("*")}
    exit_code = main(
        [
            "html-report",
            "--inventory",
            str(inventory_path),
            "--scan-artifacts",
            str(artifacts_path),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    report_path = out_dir / "findings.html"
    assert report_path.exists()
    after = {str(item) for item in tmp_path.rglob("*")}
    assert after - before == {str(out_dir), str(report_path)}


def test_cli_html_report_rejects_missing_input(tmp_path: Path):
    exit_code = main(
        [
            "html-report",
            "--inventory",
            str(tmp_path / "missing.json"),
            "--scan-artifacts",
            str(tmp_path / "missing2.json"),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 2
    assert not (tmp_path / "out" / "findings.html").exists()


def test_html_report_empty_state():
    html = render_findings_html({"root": "C:/x", "repos": [], "manifests": []}, {"artifacts": []})

    assert "No known repo-local artifacts were detected." in html
    assert "No Git repositories were discovered" in html
