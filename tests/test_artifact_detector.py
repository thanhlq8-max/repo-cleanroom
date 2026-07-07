from pathlib import Path

import pytest

from repo_cleanroom.scanner.artifact_detector import detect_artifacts


def test_detect_artifacts_classifies_safe_and_blocked(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "node_modules").mkdir()
    (repo / ".env").write_text("DO_NOT_PRINT=1", encoding="utf-8")

    records = detect_artifacts(repo, root=tmp_path)
    by_name = {Path(record.path).name: record for record in records}

    assert by_name["node_modules"].risk == "SAFE"
    assert by_name[".env"].risk == "BLOCKED"
    assert by_name[".env"].size_bytes > 0


def test_detect_artifacts_covers_additional_ecosystems(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # Regenerable build/cache/dependency dirs across ecosystems -> SAFE.
    safe_dirs = [
        ".gradle",
        ".dart_tool",
        ".turbo",
        ".svelte-kit",
        ".angular",
        "__pypackages__",
        ".hypothesis",
        ".ipynb_checkpoints",
        ".eggs",
    ]
    for name in safe_dirs:
        artifact = repo / name
        artifact.mkdir()
        (artifact / "generated.bin").write_bytes(b"x" * 8)

    records = detect_artifacts(repo, root=tmp_path)
    by_name = {Path(record.path).name: record for record in records}

    for name in safe_dirs:
        assert name in by_name, f"{name} should be detected"
        assert by_name[name].risk == "SAFE", f"{name} should classify SAFE"
        assert by_name[name].size_bytes > 0
        assert by_name[name].artifact_type


def test_detect_artifacts_runtime_dirs_stay_review(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("data", "outputs", "logs"):
        (repo / name).mkdir()

    records = detect_artifacts(repo, root=tmp_path)
    by_name = {Path(record.path).name: record for record in records}

    # Runtime data must never be promoted to SAFE by the coverage expansion.
    for name in ("data", "outputs", "logs"):
        assert by_name[name].risk == "REVIEW"


def test_detect_artifacts_finds_nested_monorepo_artifacts(tmp_path: Path):
    repo = tmp_path / "repo"
    # Monorepo layout: artifacts nested under packages/ and apps/.
    (repo / "packages" / "app-a" / "node_modules" / "dep").mkdir(parents=True)
    (repo / "packages" / "app-a" / "node_modules" / "dep" / "i.js").write_text("x", encoding="utf-8")
    (repo / "packages" / "app-b" / "dist").mkdir(parents=True)
    (repo / "packages" / "app-b" / "dist" / "b.js").write_text("y", encoding="utf-8")
    (repo / "apps" / "web" / ".next").mkdir(parents=True)
    # A nested secret must still be flagged BLOCKED wherever it lives.
    (repo / "packages" / "app-a" / ".env").write_text("K=synthetic", encoding="utf-8")
    # Plain source dirs are not artifacts.
    (repo / "packages" / "app-a" / "src").mkdir(parents=True)

    records = detect_artifacts(repo, root=tmp_path)
    by_rel = {record.relative_path: record for record in records}

    assert "packages/app-a/node_modules" in by_rel
    assert by_rel["packages/app-a/node_modules"].risk == "SAFE"
    assert "packages/app-b/dist" in by_rel
    assert "apps/web/.next" in by_rel
    assert by_rel["packages/app-a/.env"].risk == "BLOCKED"
    assert "packages/app-a/src" not in by_rel


def test_detect_artifacts_does_not_descend_into_detected_artifact(tmp_path: Path):
    repo = tmp_path / "repo"
    # Classic nested node_modules; the inner one must not be reported separately.
    inner = repo / "node_modules" / "pkg" / "node_modules"
    inner.mkdir(parents=True)
    (inner / "x.js").write_text("x", encoding="utf-8")

    records = detect_artifacts(repo, root=tmp_path)
    rels = [record.relative_path for record in records]

    assert rels == ["node_modules"], "must record only the outermost node_modules"


def test_detect_artifacts_respects_max_depth(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "a" / "b" / "node_modules").mkdir(parents=True)

    shallow = detect_artifacts(repo, root=tmp_path, max_depth=8)
    assert any(r.relative_path == "a/b/node_modules" for r in shallow)

    # With max_depth=2 the walk stops before reaching a/b, so nothing is found.
    capped = detect_artifacts(repo, root=tmp_path, max_depth=2)
    assert capped == []


def test_detect_artifacts_does_not_traverse_symlink(tmp_path: Path):
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("x", encoding="utf-8")

    link = repo / "node_modules"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this platform")

    records = detect_artifacts(repo, root=repo)

    assert len(records) == 1
    assert records[0].is_symlink is True
    assert records[0].size_bytes == 0
    assert "SYMLINK_NOT_TRAVERSED" in records[0].scan_errors
    assert "SYMLINK_TARGET_OUTSIDE_ROOT" in records[0].scan_errors
