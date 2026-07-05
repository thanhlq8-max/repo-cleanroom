import json
from pathlib import Path

from repo_cleanroom.cli import main
from repo_cleanroom.evidence.sanitizer import sanitize_line


def test_sanitize_redacts_url_credentials():
    result = sanitize_line("git clone https://user:hunter2@github.com/demo/repo.git")
    assert "hunter2" not in result
    assert "[REDACTED]@github.com" in result


def test_sanitize_redacts_sensitive_flags_and_assignments():
    flag = sanitize_line("docker login --password hunter2 registry.example.com")
    assert "hunter2" not in flag

    assign = sanitize_line("API_TOKEN=abc123def456 npm run deploy")
    assert "abc123def456" not in assign
    assert "API_TOKEN=[REDACTED]" in assign


def test_sanitize_redacts_token_shaped_strings():
    opaque = "demo0opaque1value2shape3"
    result = sanitize_line(f"curl -H {opaque}")
    assert opaque not in result
    assert "[REDACTED]" in result


def test_sanitize_collapses_lines_touching_protected_files():
    result = sanitize_line("notepad .env")
    assert result == "notepad [REDACTED-ARGS]"


def _write_inventory(tmp_path: Path) -> Path:
    inventory = {
        "schema_version": "0.1.0",
        "root": str(tmp_path / "workspace"),
        "artifacts": [
            {
                "repo_relative_path": "demo",
                "relative_path": "node_modules",
                "artifact_type": "node_dependencies",
                "risk": "SAFE",
            },
            {
                "repo_relative_path": "demo",
                "relative_path": ".venv",
                "artifact_type": "python_virtualenv",
                "risk": "SAFE",
            },
            {
                "repo_relative_path": "demo",
                "relative_path": ".env",
                "artifact_type": "protected_config",
                "risk": "BLOCKED",
            },
        ],
    }
    path = tmp_path / "artifact_inventory.json"
    path.write_text(json.dumps(inventory), encoding="utf-8")
    return path


def test_evidence_maps_commands_to_artifacts(tmp_path: Path):
    inventory_path = _write_inventory(tmp_path)
    evidence_path = tmp_path / "evidence.txt"
    evidence_path.write_text(
        "# my commands\n"
        "npm install\n"
        "py -m venv .venv\n"
        "git status\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    exit_code = main(
        [
            "evidence",
            "--evidence-file",
            str(evidence_path),
            "--scan-artifacts",
            str(inventory_path),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads((out_dir / "command_evidence.json").read_text(encoding="utf-8"))
    assert payload["mode"] == "EVIDENCE_MAPPING_ONLY"
    assert payload["summary"]["evidence_lines"] == 3
    assert payload["summary"]["classified_lines"] == 2
    assert payload["summary"]["unclassified_lines"] == 1

    by_type = {a["artifact_type"]: a for a in payload["artifacts"]}
    assert by_type["node_dependencies"]["supporting_line_indexes"] == [2]
    assert by_type["python_virtualenv"]["supporting_line_indexes"] == [3]
    assert by_type["protected_config"]["supporting_line_indexes"] == []

    report = (out_dir / "evidence_map.md").read_text(encoding="utf-8")
    assert "`npm install`" in report
    assert "git status" in report  # listed as unclassified
    assert "no shell history was read" in report


def test_evidence_outputs_never_contain_raw_secrets(tmp_path: Path):
    inventory_path = _write_inventory(tmp_path)
    evidence_path = tmp_path / "evidence.txt"
    evidence_path.write_text(
        "npm install --registry https://bot:hunter2@registry.internal\n"
        "API_TOKEN=abc123def456 pip install demo\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    assert (
        main(
            [
                "evidence",
                "--evidence-file",
                str(evidence_path),
                "--scan-artifacts",
                str(inventory_path),
                "--out-dir",
                str(out_dir),
            ]
        )
        == 0
    )

    for name in ("command_evidence.json", "evidence_map.md"):
        content = (out_dir / name).read_text(encoding="utf-8")
        assert "hunter2" not in content
        assert "abc123def456" not in content


def test_evidence_requires_explicit_file(tmp_path: Path):
    inventory_path = _write_inventory(tmp_path)

    try:
        main(
            [
                "evidence",
                "--scan-artifacts",
                str(inventory_path),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for missing required --evidence-file")


def test_evidence_missing_file_is_a_clean_error(tmp_path: Path):
    inventory_path = _write_inventory(tmp_path)

    exit_code = main(
        [
            "evidence",
            "--evidence-file",
            str(tmp_path / "does-not-exist.txt"),
            "--scan-artifacts",
            str(inventory_path),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 2
    assert not (tmp_path / "out" / "command_evidence.json").exists()


def test_evidence_does_not_touch_the_workspace(tmp_path: Path):
    inventory_path = _write_inventory(tmp_path)
    workspace = tmp_path / "workspace" / "demo" / "node_modules"
    workspace.mkdir(parents=True)
    (workspace / "keep.js").write_text("keep", encoding="utf-8")
    evidence_path = tmp_path / "evidence.txt"
    evidence_path.write_text("npm install\n", encoding="utf-8")
    before = {str(item) for item in (tmp_path / "workspace").rglob("*")}

    assert (
        main(
            [
                "evidence",
                "--evidence-file",
                str(evidence_path),
                "--scan-artifacts",
                str(inventory_path),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )

    assert {str(item) for item in (tmp_path / "workspace").rglob("*")} == before
