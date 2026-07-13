import json
from pathlib import Path

import pytest

from repo_cleanroom.cli import main
from repo_cleanroom.scanner.artifact_detector import detect_artifacts
from repo_cleanroom.scanner.scan_config import (
    ScanConfig,
    ScanConfigError,
    load_scan_config,
)


def _write_config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "cleanroom.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_load_scan_config_reads_ignore_and_extra(tmp_path: Path):
    path = _write_config(
        tmp_path,
        'ignore = ["vendor", "packages/legacy/*"]\nextra_artifact_names = [".mycache"]\n',
    )
    config = load_scan_config(path)
    assert config.ignore == ("vendor", "packages/legacy/*")
    assert config.extra_artifact_names == (".mycache",)


def test_load_scan_config_rejects_unknown_key(tmp_path: Path):
    path = _write_config(tmp_path, 'ignroe = ["typo"]\n')
    with pytest.raises(ScanConfigError):
        load_scan_config(path)


def test_load_scan_config_rejects_wrong_type(tmp_path: Path):
    path = _write_config(tmp_path, 'ignore = "not-a-list"\n')
    with pytest.raises(ScanConfigError):
        load_scan_config(path)


def test_load_scan_config_missing_file(tmp_path: Path):
    with pytest.raises(ScanConfigError):
        load_scan_config(tmp_path / "nope.toml")


def test_load_scan_config_tolerates_utf8_bom(tmp_path: Path):
    # Windows editors (Notepad, PowerShell Out-File) prepend a UTF-8 BOM.
    path = tmp_path / "bom.toml"
    path.write_bytes(b"\xef\xbb\xbf" + b'ignore = ["vendor"]\n')
    config = load_scan_config(path)
    assert config.ignore == ("vendor",)


def test_ignore_prunes_by_basename_anywhere(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "node_modules").mkdir(parents=True)
    (repo / "packages" / "app" / "node_modules").mkdir(parents=True)
    (repo / "packages" / "app" / "dist").mkdir(parents=True)

    config = ScanConfig(ignore=("node_modules",))
    rels = {r.relative_path for r in detect_artifacts(repo, root=tmp_path, config=config)}

    assert "packages/app/dist" in rels
    assert not any("node_modules" in rel for rel in rels)


def test_ignore_prunes_by_path_glob(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "packages" / "legacy" / "dist").mkdir(parents=True)
    (repo / "packages" / "active" / "dist").mkdir(parents=True)

    config = ScanConfig(ignore=("packages/legacy/*",))
    rels = {r.relative_path for r in detect_artifacts(repo, root=tmp_path, config=config)}

    assert "packages/active/dist" in rels
    assert "packages/legacy/dist" not in rels


def test_extra_artifact_names_detected_as_review(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / ".mycache").mkdir(parents=True)
    (repo / ".mycache" / "x").write_text("y", encoding="utf-8")

    config = ScanConfig(extra_artifact_names=(".mycache",))
    records = detect_artifacts(repo, root=tmp_path, config=config)
    by_rel = {r.relative_path: r for r in records}

    assert ".mycache" in by_rel
    # Custom names are never auto-SAFE: they classify REVIEW so removal still needs review.
    assert by_rel[".mycache"].risk == "REVIEW"
    assert by_rel[".mycache"].artifact_type == "custom_configured"


def test_scan_cli_applies_config_and_records_it(tmp_path: Path):
    root = tmp_path / "workspace"
    repo = root / "demo"
    (repo / ".git").mkdir(parents=True)
    (repo / "node_modules").mkdir()
    (repo / "dist").mkdir()
    (repo / ".mycache").mkdir()

    config_path = _write_config(
        tmp_path,
        'ignore = ["dist"]\nextra_artifact_names = [".mycache"]\n',
    )
    out_dir = tmp_path / "out"
    exit_code = main(
        ["scan", "--root", str(root), "--out-dir", str(out_dir), "--config", str(config_path)]
    )

    assert exit_code == 0
    inventory = json.loads((out_dir / "artifact_inventory.json").read_text(encoding="utf-8"))
    rels = {a["relative_path"] for a in inventory["artifacts"]}
    assert "node_modules" in rels
    assert "dist" not in rels, "ignored path must be excluded"
    assert ".mycache" in rels, "extra artifact name must be detected"
    assert inventory["scan_config"] == {
        "ignore": ["dist"],
        "extra_artifact_names": [".mycache"],
        "max_depth": None,
    }


def test_scan_cli_rejects_bad_config(tmp_path: Path):
    root = tmp_path / "workspace"
    (root / "demo" / ".git").mkdir(parents=True)
    config_path = _write_config(tmp_path, "this is not = valid toml [[[\n")

    exit_code = main(
        ["scan", "--root", str(root), "--out-dir", str(tmp_path / "out"), "--config", str(config_path)]
    )
    assert exit_code == 2


def test_scan_without_config_records_empty(tmp_path: Path):
    root = tmp_path / "workspace"
    (root / "demo" / ".git").mkdir(parents=True)
    (root / "demo" / "node_modules").mkdir()

    out_dir = tmp_path / "out"
    assert main(["scan", "--root", str(root), "--out-dir", str(out_dir)]) == 0
    inventory = json.loads((out_dir / "artifact_inventory.json").read_text(encoding="utf-8"))
    assert inventory["scan_config"] == {
        "ignore": [],
        "extra_artifact_names": [],
        "max_depth": None,
    }


def test_config_max_depth_overrides_default(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "a" / "b" / "node_modules").mkdir(parents=True)

    from repo_cleanroom.scanner.artifact_detector import detect_artifacts
    from repo_cleanroom.scanner.scan_config import ScanConfig

    # Default depth (8) finds it; a config cap of 2 stops before a/b.
    assert any(
        r.relative_path == "a/b/node_modules"
        for r in detect_artifacts(repo, root=tmp_path, config=ScanConfig())
    )
    capped = detect_artifacts(repo, root=tmp_path, config=ScanConfig(max_depth=2))
    assert capped == []


def test_load_scan_config_reads_max_depth(tmp_path: Path):
    path = _write_config(tmp_path, "max_depth = 12\n")
    assert load_scan_config(path).max_depth == 12


def test_load_scan_config_rejects_bad_max_depth(tmp_path: Path):
    for bad in ("max_depth = 0\n", "max_depth = -3\n", 'max_depth = "deep"\n', "max_depth = true\n"):
        path = _write_config(tmp_path, bad)
        with pytest.raises(ScanConfigError):
            load_scan_config(path)
