"""Shared data models for Repo Cleanroom.

The models intentionally use only the Python standard library so the scanner
can run with minimal installation friction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "0.1.0"


@dataclass(frozen=True)
class RepoRecord:
    """A discovered Git repository."""

    name: str
    path: str
    relative_path: str
    git_dir: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManifestRecord:
    """A project manifest or lockfile detected inside a repository."""

    repo_path: str
    path: str
    relative_path: str
    ecosystem: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactRecord:
    """A repo-local artifact finding.

    A finding is evidence only. It is not approval to delete anything.
    """

    repo_path: str
    path: str
    relative_path: str
    artifact_type: str
    risk: str
    reason: str
    size_bytes: int
    file_count: int
    is_symlink: bool = False
    scan_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
