"""Git repository discovery."""

from __future__ import annotations

import os
from pathlib import Path

from repo_cleanroom.models import RepoRecord
from repo_cleanroom.safety.path_guard import relative_to_root, resolve_existing_directory

_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    ".nox",
    "dist",
    "build",
    "target",
}


def discover_repositories(root: str | Path) -> list[RepoRecord]:
    """Discover Git repositories under root without running git commands."""

    resolved_root = resolve_existing_directory(root)
    records: list[RepoRecord] = []

    for current, dirnames, _filenames in os.walk(resolved_root, followlinks=False):
        current_path = Path(current)
        if ".git" in dirnames:
            git_dir = current_path / ".git"
            records.append(
                RepoRecord(
                    name=current_path.name,
                    path=str(current_path),
                    relative_path=relative_to_root(resolved_root, current_path),
                    git_dir=str(git_dir),
                )
            )
            # Do not scan nested folders under an already discovered repo during
            # discovery. Artifact scanning handles each repo separately.
            dirnames[:] = []
            continue

        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIR_NAMES]

    return sorted(records, key=lambda item: item.relative_path.lower())
