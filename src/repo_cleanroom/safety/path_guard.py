"""Root path validation and boundary checks."""

from __future__ import annotations

from pathlib import Path


class PathGuardError(ValueError):
    """Raised when a path fails root-scope validation."""


def resolve_existing_directory(path: str | Path) -> Path:
    """Return an existing directory as an absolute resolved path."""

    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise PathGuardError(f"root does not exist: {candidate}")
    if not candidate.is_dir():
        raise PathGuardError(f"root is not a directory: {candidate}")
    return candidate.resolve(strict=True)


def resolve_existing_path(path: str | Path) -> Path:
    """Return an existing path as an absolute resolved path."""

    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise PathGuardError(f"path does not exist: {candidate}")
    return candidate.resolve(strict=True)


def is_within_root(root: str | Path, candidate: str | Path) -> bool:
    """Return True when candidate resolves inside root or equals root."""

    resolved_root = Path(root).resolve(strict=True)
    resolved_candidate = Path(candidate).resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True


def ensure_within_root(root: str | Path, candidate: str | Path) -> Path:
    """Resolve candidate and raise if it escapes root."""

    resolved_candidate = resolve_existing_path(candidate)
    if not is_within_root(root, resolved_candidate):
        raise PathGuardError(f"path escapes root: {resolved_candidate}")
    return resolved_candidate


def relative_to_root(root: str | Path, candidate: str | Path) -> str:
    """Return POSIX-style relative path from root to candidate."""

    resolved_root = Path(root).resolve(strict=True)
    resolved_candidate = Path(candidate).resolve(strict=True)
    return resolved_candidate.relative_to(resolved_root).as_posix()
