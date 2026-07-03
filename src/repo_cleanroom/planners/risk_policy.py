"""Risk classification policy for scan findings.

This module classifies findings only. It does not approve deletion.
"""

from __future__ import annotations

from pathlib import Path

from repo_cleanroom.safety.secret_guard import protected_reason

SAFE_ARTIFACT_NAMES = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "dist",
    "build",
    "coverage",
    ".coverage",
    ".next",
    ".nuxt",
    "target",
    "bin",
    "obj",
}

REVIEW_ARTIFACT_NAMES = {
    "data",
    "artifacts",
    "outputs",
    "output",
    "logs",
    "log",
    "tmp",
    "temp",
    ".cache",
}

DANGEROUS_ARTIFACT_NAMES = {
    "docker-volume",
    "registry-entry",
    "windows-service",
    "scheduled-task",
    "global-package",
}


def classify_path(path: str | Path, artifact_type: str | None = None) -> tuple[str, str]:
    """Classify a path into SAFE, REVIEW, DANGEROUS, or BLOCKED."""

    protected = protected_reason(path)
    if protected is not None:
        return "BLOCKED", protected

    p = Path(path)
    name = p.name
    lower_name = name.lower()
    normalized_type = (artifact_type or "").lower()

    if normalized_type in DANGEROUS_ARTIFACT_NAMES or lower_name in DANGEROUS_ARTIFACT_NAMES:
        return "DANGEROUS", "external/system or high-impact artifact class"

    if name in SAFE_ARTIFACT_NAMES or lower_name in SAFE_ARTIFACT_NAMES:
        return "SAFE", "common repo-local generated artifact"

    if name in REVIEW_ARTIFACT_NAMES or lower_name in REVIEW_ARTIFACT_NAMES:
        return "REVIEW", "may contain user/runtime data; requires review"

    if p.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".parquet", ".csv"}:
        return "REVIEW", "data-like file extension; requires review"

    return "REVIEW", "unclassified artifact; requires review"
