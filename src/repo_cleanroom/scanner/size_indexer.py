"""Read-only disk usage estimation."""

from __future__ import annotations

import os
from pathlib import Path

from repo_cleanroom.safety.symlink_guard import is_link_like


def estimate_path_size(path: str | Path) -> tuple[int, int, list[str]]:
    """Estimate size and file count without following symlinks or junctions.

    Returns (size_bytes, file_count, errors). `os.walk(followlinks=False)` still
    descends into Windows junctions, so link-like directories are pruned explicitly.
    """

    candidate = Path(path)
    errors: list[str] = []

    if is_link_like(candidate):
        return 0, 0, ["SYMLINK_NOT_TRAVERSED"]

    if candidate.is_file():
        try:
            return candidate.stat().st_size, 1, []
        except OSError as exc:
            return 0, 0, [f"STAT_ERROR:{exc.__class__.__name__}"]

    if not candidate.is_dir():
        return 0, 0, ["UNSUPPORTED_PATH_TYPE"]

    total = 0
    count = 0
    for current, dirnames, filenames in os.walk(candidate, followlinks=False):
        current_path = Path(current)

        kept_dirs = []
        for dirname in dirnames:
            child_dir = current_path / dirname
            if is_link_like(child_dir):
                errors.append(f"SYMLINK_DIR_SKIPPED:{child_dir.name}")
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            child = current_path / filename
            if is_link_like(child):
                errors.append(f"SYMLINK_FILE_SKIPPED:{child.name}")
                continue
            try:
                total += child.stat().st_size
                count += 1
            except OSError as exc:
                errors.append(f"STAT_ERROR:{exc.__class__.__name__}:{child.name}")

    return total, count, errors
