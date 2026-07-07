"""Project manifest detection."""

from __future__ import annotations

from pathlib import Path

from repo_cleanroom.models import ManifestRecord

_MANIFESTS: dict[str, tuple[str, str]] = {
    "package.json": ("node", "manifest"),
    "package-lock.json": ("node", "lockfile"),
    "pnpm-lock.yaml": ("node", "lockfile"),
    "yarn.lock": ("node", "lockfile"),
    "pyproject.toml": ("python", "manifest"),
    "requirements.txt": ("python", "manifest"),
    "requirements-dev.txt": ("python", "manifest"),
    "poetry.lock": ("python", "lockfile"),
    "Pipfile": ("python", "manifest"),
    "Pipfile.lock": ("python", "lockfile"),
    "environment.yml": ("python", "manifest"),
    "environment.yaml": ("python", "manifest"),
    "Dockerfile": ("docker", "manifest"),
    "docker-compose.yml": ("docker", "manifest"),
    "docker-compose.yaml": ("docker", "manifest"),
    "compose.yml": ("docker", "manifest"),
    "compose.yaml": ("docker", "manifest"),
    "go.mod": ("go", "manifest"),
    "go.sum": ("go", "lockfile"),
    "Cargo.toml": ("rust", "manifest"),
    "Cargo.lock": ("rust", "lockfile"),
    "pom.xml": ("java", "manifest"),
    "build.gradle": ("java", "manifest"),
    "build.gradle.kts": ("java", "manifest"),
    "settings.gradle": ("java", "manifest"),
    "settings.gradle.kts": ("java", "manifest"),
    "composer.json": ("php", "manifest"),
    "composer.lock": ("php", "lockfile"),
    "Gemfile": ("ruby", "manifest"),
    "Gemfile.lock": ("ruby", "lockfile"),
    "pubspec.yaml": ("dart", "manifest"),
    "pubspec.lock": ("dart", "lockfile"),
    "deno.json": ("deno", "manifest"),
    "deno.jsonc": ("deno", "manifest"),
    "bun.lockb": ("node", "lockfile"),
    "Makefile": ("build", "manifest"),
    "Taskfile.yml": ("build", "manifest"),
    "Taskfile.yaml": ("build", "manifest"),
}

_DOTNET_SUFFIXES = {".sln", ".csproj", ".fsproj", ".vbproj"}


def detect_manifests(repo_path: str | Path) -> list[ManifestRecord]:
    """Detect known manifest/lock files in the repository root."""

    root = Path(repo_path)
    records: list[ManifestRecord] = []

    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_file():
            continue

        mapping = _MANIFESTS.get(child.name)
        if mapping is None and child.suffix.lower() in _DOTNET_SUFFIXES:
            mapping = ("dotnet", "manifest")
        if mapping is None:
            continue

        ecosystem, kind = mapping
        records.append(
            ManifestRecord(
                repo_path=str(root),
                path=str(child),
                relative_path=child.name,
                ecosystem=ecosystem,
                kind=kind,
            )
        )

    return records
