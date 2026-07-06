"""Symlink and reparse-point inspection helpers.

Scan operations must not follow symlinks while estimating artifact size.

Windows junctions and mount points are reparse points that `Path.is_symlink()`
reports as False on every supported Python version, and `os.walk(followlinks=False)`
still descends into them. Any boundary decision must therefore use
:func:`is_link_like`, never `is_symlink()` alone.
"""

from __future__ import annotations

import os
import stat as stat_module
from dataclasses import dataclass
from pathlib import Path

from repo_cleanroom.safety.path_guard import is_within_root


@dataclass(frozen=True)
class SymlinkFinding:
    path: str
    is_symlink: bool
    target: str | None
    target_inside_root: bool | None


def is_reparse_point(path: str | Path) -> bool:
    """Return True for any Windows reparse point (junction, mount point, symlink).

    Always False on POSIX. Uses lstat so the reparse point itself is examined,
    never its target.
    """

    try:
        st = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(st, "st_file_attributes", 0)
    return bool(attributes & stat_module.FILE_ATTRIBUTE_REPARSE_POINT)


def is_link_like(path: str | Path) -> bool:
    """Return True when path is a boundary that must never be traversed.

    Covers real symlinks on every OS plus non-symlink reparse points
    (junctions, mount points) on Windows.
    """

    return Path(path).is_symlink() or is_reparse_point(path)


def inspect_symlink(root: str | Path, path: str | Path) -> SymlinkFinding:
    """Inspect a path and report whether it is link-like and where it points.

    Junctions and mount points are reported with ``is_symlink=True``: for every
    safety decision downstream they must behave exactly like a symlink.
    """

    candidate = Path(path)
    if not is_link_like(candidate):
        return SymlinkFinding(
            path=str(candidate),
            is_symlink=False,
            target=None,
            target_inside_root=None,
        )

    try:
        target = candidate.resolve(strict=True)
        inside = is_within_root(root, target)
        target_text: str | None = str(target)
    except OSError:
        inside = False
        target_text = None

    return SymlinkFinding(
        path=str(candidate),
        is_symlink=True,
        target=target_text,
        target_inside_root=inside,
    )
