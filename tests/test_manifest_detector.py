from pathlib import Path

from repo_cleanroom.scanner.manifest_detector import detect_manifests


def test_detect_manifests(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'", encoding="utf-8")
    (tmp_path / "demo.sln").write_text("", encoding="utf-8")

    records = detect_manifests(tmp_path)
    ecosystems = sorted((record.ecosystem, record.kind) for record in records)

    assert ("node", "manifest") in ecosystems
    assert ("python", "manifest") in ecosystems
    assert ("dotnet", "manifest") in ecosystems
