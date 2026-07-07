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


def test_detect_manifests_additional_ecosystems(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    (tmp_path / "build.gradle.kts").write_text("", encoding="utf-8")
    (tmp_path / "composer.json").write_text("{}", encoding="utf-8")
    (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'", encoding="utf-8")
    (tmp_path / "pubspec.yaml").write_text("name: demo", encoding="utf-8")
    (tmp_path / "deno.json").write_text("{}", encoding="utf-8")

    records = detect_manifests(tmp_path)
    ecosystems = {record.ecosystem for record in records}

    assert {"java", "php", "ruby", "dart", "deno"}.issubset(ecosystems)
    # Gradle and Maven both report the java ecosystem.
    java = sorted(Path(r.path).name for r in records if r.ecosystem == "java")
    assert java == ["build.gradle.kts", "pom.xml"]
