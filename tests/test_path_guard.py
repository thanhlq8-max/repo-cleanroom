from pathlib import Path

import pytest

from repo_cleanroom.safety.path_guard import (
    PathGuardError,
    ensure_within_root,
    is_within_root,
    relative_to_root,
    resolve_existing_directory,
)


def test_resolve_existing_directory_requires_directory(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(PathGuardError):
        resolve_existing_directory(file_path)


def test_resolve_existing_directory_returns_resolved_path(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()

    assert resolve_existing_directory(root) == root.resolve()


def test_ensure_within_root_allows_child(tmp_path: Path):
    child = tmp_path / "repo"
    child.mkdir()

    assert ensure_within_root(tmp_path, child) == child.resolve()


def test_ensure_within_root_allows_root_itself(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()

    assert ensure_within_root(root, root) == root.resolve()


def test_ensure_within_root_rejects_sibling_directory(tmp_path: Path):
    root = tmp_path / "workspace"
    sibling = tmp_path / "workspace-other"
    root.mkdir()
    sibling.mkdir()

    with pytest.raises(PathGuardError):
        ensure_within_root(root, sibling)


def test_ensure_within_root_rejects_sibling_with_similar_prefix(tmp_path: Path):
    root = tmp_path / "repo"
    sibling = tmp_path / "repo-cache"
    root.mkdir()
    sibling.mkdir()

    assert is_within_root(root, root) is True
    assert is_within_root(root, sibling) is False
    with pytest.raises(PathGuardError):
        ensure_within_root(root, sibling)


def test_ensure_within_root_handles_dotdot_inside_root(tmp_path: Path):
    root = tmp_path / "workspace"
    repo = root / "repo"
    nested = repo / "nested"
    nested.mkdir(parents=True)

    candidate = nested / ".."

    assert ensure_within_root(root, candidate) == repo.resolve()


def test_relative_to_root_uses_posix_separator(tmp_path: Path):
    root = tmp_path / "workspace"
    nested = root / "repo" / "child"
    nested.mkdir(parents=True)

    assert relative_to_root(root, nested) == "repo/child"


def test_ensure_within_root_rejects_missing_candidate(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()

    with pytest.raises(PathGuardError):
        ensure_within_root(root, root / "missing")


def test_ensure_within_root_rejects_symlink_to_sibling(tmp_path: Path):
    root = tmp_path / "workspace"
    sibling = tmp_path / "external-data"
    root.mkdir()
    sibling.mkdir()

    link = root / "linked-data"
    try:
        link.symlink_to(sibling, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this platform")

    with pytest.raises(PathGuardError):
        ensure_within_root(root, link)
