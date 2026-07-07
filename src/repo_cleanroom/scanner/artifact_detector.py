"""Repo-local artifact detection."""

from __future__ import annotations

import os
from pathlib import Path

from repo_cleanroom.models import ArtifactRecord, ManifestRecord
from repo_cleanroom.planners.risk_policy import classify_path
from repo_cleanroom.safety.symlink_guard import inspect_symlink, is_link_like
from repo_cleanroom.scanner.size_indexer import estimate_path_size

# VCS internals / nested-repo boundaries are never scanned as artifacts.
_VCS_DIR_NAMES = {".git", ".hg", ".svn"}

# Bound on repo-relative directory depth for nested detection. Detected artifacts
# prune the walk, so realistic monorepos stay shallow; this caps pathological trees.
DEFAULT_MAX_DEPTH = 8

# Detection is name-based and repo-local. Names map to a descriptive artifact_type
# (not a frozen schema enum); risk is assigned separately by the risk policy. New
# entries are additive — see docs/SCHEMA_STABILITY.md.
ARTIFACT_NAMES = {
    # Node / JS
    "node_modules": "node_dependencies",
    ".next": "node_build_output",
    ".nuxt": "node_build_output",
    ".output": "node_build_output",
    ".svelte-kit": "node_build_output",
    ".astro": "node_build_output",
    ".turbo": "node_build_cache",
    ".parcel-cache": "node_build_cache",
    ".angular": "node_build_cache",
    # Python
    ".venv": "python_virtualenv",
    "venv": "python_virtualenv",
    "__pypackages__": "python_dependencies",
    "__pycache__": "python_cache",
    ".pytest_cache": "python_cache",
    ".mypy_cache": "python_cache",
    ".ruff_cache": "python_cache",
    ".hypothesis": "python_cache",
    ".ipynb_checkpoints": "jupyter_checkpoint",
    ".eggs": "python_build_output",
    ".tox": "python_test_env",
    ".nox": "python_test_env",
    # Generic build / coverage
    "dist": "build_output",
    "build": "build_output",
    "coverage": "coverage_output",
    ".coverage": "coverage_output",
    # Rust / JVM / .NET / Dart
    "target": "rust_build_output",
    ".gradle": "gradle_cache",
    ".dart_tool": "dart_build_cache",
    "bin": "dotnet_build_output",
    "obj": "dotnet_build_output",
    # Runtime data (review-required, not auto-safe)
    "data": "runtime_data",
    "artifacts": "runtime_artifacts",
    "outputs": "runtime_outputs",
    "output": "runtime_outputs",
    "logs": "runtime_logs",
    "log": "runtime_logs",
    "tmp": "temporary_output",
    "temp": "temporary_output",
    ".cache": "local_cache",
    # Protected (never auto-deletable)
    ".env": "protected_config",
    ".env.local": "protected_config",
    "credentials.json": "protected_credentials",
}


def _lookup_type(name: str) -> str | None:
    artifact_type = ARTIFACT_NAMES.get(name)
    if artifact_type is None:
        artifact_type = ARTIFACT_NAMES.get(name.lower())
    return artifact_type


def _build_record(repo: Path, scan_root: Path, candidate: Path) -> ArtifactRecord:
    artifact_type = _lookup_type(candidate.name)
    symlink = inspect_symlink(scan_root, candidate)
    if symlink.is_symlink:
        size_bytes = 0
        file_count = 0
        errors = ["SYMLINK_NOT_TRAVERSED"]
        if symlink.target_inside_root is False:
            errors.append("SYMLINK_TARGET_OUTSIDE_ROOT")
    else:
        size_bytes, file_count, errors = estimate_path_size(candidate)

    risk, reason = classify_path(candidate, artifact_type)
    return ArtifactRecord(
        repo_path=str(repo),
        path=str(candidate),
        relative_path=candidate.relative_to(repo).as_posix(),
        artifact_type=artifact_type,
        risk=risk,
        reason=reason,
        size_bytes=size_bytes,
        file_count=file_count,
        is_symlink=symlink.is_symlink,
        scan_errors=errors,
    )


def detect_artifacts(
    repo_path: str | Path,
    manifests: list[ManifestRecord] | None = None,
    root: str | Path | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> list[ArtifactRecord]:
    """Detect repo-local artifacts, including nested ones in monorepos.

    Walks the repository tree without following symlinks or junctions. A matched
    artifact directory is recorded and never descended into (so artifacts inside
    artifacts, e.g. nested ``node_modules``, are not double-reported and its own
    subtree is not walked). VCS internals (``.git``/``.hg``/``.svn``) are skipped;
    descent is bounded by ``max_depth`` (repo-relative). ``relative_path`` is the
    POSIX path from the repo root, so top-level artifacts keep their bare name.
    """

    del manifests  # Reserved for future classifier refinement.
    repo = Path(repo_path)
    scan_root = Path(root) if root is not None else repo
    records: list[ArtifactRecord] = []

    for current, dirnames, filenames in os.walk(repo, followlinks=False):
        current_path = Path(current)
        depth = 0 if current_path == repo else len(current_path.relative_to(repo).parts)

        for filename in filenames:
            if _lookup_type(filename) is not None:
                records.append(_build_record(repo, scan_root, current_path / filename))

        kept: list[str] = []
        for dirname in dirnames:
            child = current_path / dirname
            if dirname in _VCS_DIR_NAMES:
                continue
            if _lookup_type(dirname) is not None:
                # Record the artifact, then prune: never descend into it.
                records.append(_build_record(repo, scan_root, child))
                continue
            if is_link_like(child):
                # Never traverse symlinks/junctions during discovery.
                continue
            if depth + 1 >= max_depth:
                continue
            kept.append(dirname)
        dirnames[:] = kept

    return sorted(records, key=lambda item: item.relative_path.lower())
