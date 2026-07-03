"""Repo-local artifact detection."""

from __future__ import annotations

from pathlib import Path

from repo_cleanroom.models import ArtifactRecord, ManifestRecord
from repo_cleanroom.planners.risk_policy import classify_path
from repo_cleanroom.safety.symlink_guard import inspect_symlink
from repo_cleanroom.scanner.size_indexer import estimate_path_size

# Detection is name-based and repo-local in v0.1.0.
ARTIFACT_NAMES = {
    "node_modules": "node_dependencies",
    ".next": "node_build_output",
    ".nuxt": "node_build_output",
    ".venv": "python_virtualenv",
    "venv": "python_virtualenv",
    "__pycache__": "python_cache",
    ".pytest_cache": "python_cache",
    ".mypy_cache": "python_cache",
    ".ruff_cache": "python_cache",
    ".tox": "python_test_env",
    ".nox": "python_test_env",
    "dist": "build_output",
    "build": "build_output",
    "coverage": "coverage_output",
    ".coverage": "coverage_output",
    "target": "rust_build_output",
    "bin": "dotnet_build_output",
    "obj": "dotnet_build_output",
    "data": "runtime_data",
    "artifacts": "runtime_artifacts",
    "outputs": "runtime_outputs",
    "output": "runtime_outputs",
    "logs": "runtime_logs",
    "log": "runtime_logs",
    "tmp": "temporary_output",
    "temp": "temporary_output",
    ".cache": "local_cache",
    ".env": "protected_config",
    ".env.local": "protected_config",
    "credentials.json": "protected_credentials",
}


def detect_artifacts(
    repo_path: str | Path,
    manifests: list[ManifestRecord] | None = None,
    root: str | Path | None = None,
) -> list[ArtifactRecord]:
    """Detect top-level repo-local artifacts.

    The detector does not recurse into arbitrary subtrees looking for every
    possible artifact. v0.1.0 intentionally starts with top-level generated
    items to reduce false positives and runtime cost.
    """

    del manifests  # Reserved for future classifier refinement.
    repo = Path(repo_path)
    scan_root = Path(root) if root is not None else repo
    records: list[ArtifactRecord] = []

    for child in sorted(repo.iterdir(), key=lambda p: p.name.lower()):
        artifact_type = ARTIFACT_NAMES.get(child.name)
        if artifact_type is None:
            artifact_type = ARTIFACT_NAMES.get(child.name.lower())
        if artifact_type is None:
            continue

        symlink = inspect_symlink(scan_root, child)
        if symlink.is_symlink:
            size_bytes = 0
            file_count = 0
            errors = ["SYMLINK_NOT_TRAVERSED"]
            if symlink.target_inside_root is False:
                errors.append("SYMLINK_TARGET_OUTSIDE_ROOT")
        else:
            size_bytes, file_count, errors = estimate_path_size(child)

        risk, reason = classify_path(child, artifact_type)
        records.append(
            ArtifactRecord(
                repo_path=str(repo),
                path=str(child),
                relative_path=child.name,
                artifact_type=artifact_type,
                risk=risk,
                reason=reason,
                size_bytes=size_bytes,
                file_count=file_count,
                is_symlink=symlink.is_symlink,
                scan_errors=errors,
            )
        )

    return records
