"""Build docker_inventory.json from read-only docker CLI queries.

Design decision (v0.6.0): Docker is queried by invoking the user's `docker` CLI
with a FIXED whitelist of read-only argument lists (`shell=False`, no user input
in argv). The Engine API/SDK was rejected (would add a dependency; the project is
stdlib-only) and reading Docker's on-disk metadata was rejected (fragile,
invasive). Mutation is impossible by construction: only whitelisted argv lists
can reach subprocess, and none of them mutates state.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DOCKER_INVENTORY_SCHEMA_VERSION = "0.6.0"

_JSON_FORMAT = "{{json .}}"

# The ONLY docker invocations this package may perform. Read-only by inspection.
ALLOWED_QUERIES: dict[str, list[str]] = {
    "version": ["version", "--format", _JSON_FORMAT],
    "containers": ["ps", "--all", "--no-trunc", "--format", _JSON_FORMAT],
    "images": ["images", "--format", _JSON_FORMAT],
    "volumes": ["volume", "ls", "--format", _JSON_FORMAT],
}

_COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
_COMPOSE_WORKING_DIR_LABEL = "com.docker.compose.project.working_dir"


class DockerScanError(ValueError):
    """Raised when Docker cannot be queried read-only."""


Runner = Callable[[list[str]], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_runner(argv: list[str]) -> str:
    """Run one whitelisted docker query and return stdout text."""

    completed = subprocess.run(
        ["docker", *argv],
        capture_output=True,
        text=True,
        timeout=30,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        raise DockerScanError(
            f"docker {' '.join(argv[:2])} failed: {completed.stderr.strip() or 'unknown error'}"
        )
    return completed.stdout


def run_query(name: str, runner: Runner) -> str:
    """Execute a query by whitelist name only. Anything else is refused."""

    if name not in ALLOWED_QUERIES:
        raise DockerScanError(f"docker query not in read-only whitelist: {name!r}")
    return runner(ALLOWED_QUERIES[name])


def _parse_json_lines(text: str) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    errors = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            errors += 1
            continue
        if isinstance(payload, dict):
            records.append(payload)
        else:
            errors += 1
    return records, errors


def _parse_labels(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for part in (raw or "").split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            labels[key.strip()] = value.strip()
    return labels


def _is_under_root(root: Path, candidate: str) -> bool:
    if not candidate:
        return False
    try:
        normalized_root = os.path.normcase(str(root))
        normalized_candidate = os.path.normcase(str(Path(candidate)))
    except (OSError, ValueError):
        return False
    return normalized_candidate == normalized_root or normalized_candidate.startswith(
        normalized_root + os.sep
    )


def build_docker_inventory(root: Path, runner: Runner | None = None) -> dict[str, Any]:
    """Query Docker read-only and relate objects to the selected workspace root."""

    active_runner = runner or default_runner

    try:
        run_query("version", active_runner)
    except (DockerScanError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise DockerScanError(f"docker is not available for read-only query: {exc}") from exc

    parse_errors = 0

    raw_containers, errors = _parse_json_lines(run_query("containers", active_runner))
    parse_errors += errors
    containers = []
    for record in raw_containers:
        labels = _parse_labels(record.get("Labels", ""))
        working_dir = labels.get(_COMPOSE_WORKING_DIR_LABEL, "")
        containers.append(
            {
                "id": record.get("ID"),
                "name": record.get("Names"),
                "image": record.get("Image"),
                "state": record.get("State"),
                "status": record.get("Status"),
                "compose_project": labels.get(_COMPOSE_PROJECT_LABEL),
                "compose_working_dir": working_dir or None,
                "linked_to_workspace": _is_under_root(root, working_dir),
            }
        )

    raw_images, errors = _parse_json_lines(run_query("images", active_runner))
    parse_errors += errors
    images = []
    for record in raw_images:
        repository = record.get("Repository", "")
        images.append(
            {
                "id": record.get("ID"),
                "repository": repository,
                "tag": record.get("Tag"),
                "size": record.get("Size"),
                "dangling": repository in ("", "<none>"),
            }
        )

    raw_volumes, errors = _parse_json_lines(run_query("volumes", active_runner))
    parse_errors += errors
    volumes = []
    for record in raw_volumes:
        labels = _parse_labels(record.get("Labels", ""))
        working_dir = labels.get(_COMPOSE_WORKING_DIR_LABEL, "")
        volumes.append(
            {
                "name": record.get("Name"),
                "driver": record.get("Driver"),
                "compose_project": labels.get(_COMPOSE_PROJECT_LABEL),
                "linked_to_workspace": _is_under_root(root, working_dir),
            }
        )

    return {
        "docker_inventory_schema_version": DOCKER_INVENTORY_SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "mode": "DOCKER_READ_ONLY_SCAN",
        "root": str(root),
        "containers": containers,
        "images": images,
        "volumes": volumes,
        "summary": {
            "containers": len(containers),
            "containers_linked_to_workspace": sum(
                1 for item in containers if item["linked_to_workspace"]
            ),
            "images": len(images),
            "dangling_images": sum(1 for item in images if item["dangling"]),
            "volumes": len(volumes),
            "parse_errors": parse_errors,
        },
        "safety": {
            "docker_mutation_performed": False,
            "queries_used": sorted(ALLOWED_QUERIES),
        },
    }
