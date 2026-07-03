"""Symlink inspection helpers.

Scan operations must not follow symlinks while estimating artifact size.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repo_cleanroom.safety.path_guard import is_within_root


@dataclass(frozen=True)
class SymlinkFinding:
    path: str
    is_symlink: bool
    target: str | None
    target_inside_root: bool | None


def inspect_symlink(root: str | Path, path: str | Path) -> SymlinkFinding:
    """Inspect a path and report whether it is a symlink and where it points."""

    candidate = Path(path)
    if not candidate.is_symlink():
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
