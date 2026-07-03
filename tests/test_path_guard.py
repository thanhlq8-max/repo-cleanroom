from pathlib import Path

import pytest

from repo_cleanroom.safety.path_guard import PathGuardError, ensure_within_root, resolve_existing_directory


def test_resolve_existing_directory_requires_directory(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(PathGuardError):
        resolve_existing_directory(file_path)


def test_ensure_within_root_allows_child(tmp_path: Path):
    child = tmp_path / "repo"
    child.mkdir()

    assert ensure_within_root(tmp_path, child) == child.resolve()


def test_ensure_within_root_blocks_escape(tmp_path: Path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    with pytest.raises(PathGuardError):
        ensure_within_root(root, outside)
