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
