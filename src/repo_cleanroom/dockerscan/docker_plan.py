"""Build docker_cleanup_plan.json from an existing docker inventory.

The Docker plan is informational only. This tool has NO Docker mutation
capability: no command exists that could act on this plan. Volumes are never
proposed for deletion. Fixed policy:

- exited/created container linked to the workspace -> REVIEW_REQUIRED
- any other container                              -> NO_ACTION
- dangling image                                   -> REVIEW_REQUIRED
- any other image                                  -> NO_ACTION
- every volume                                     -> FORBIDDEN_DEFAULT
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOCKER_PLAN_SCHEMA_VERSION = "0.6.0"

_STOPPED_STATES = {"exited", "created", "dead"}


class DockerPlanError(ValueError):
    """Raised when the docker inventory cannot produce a plan."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_inventory(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DockerPlanError(f"docker inventory is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DockerPlanError("docker inventory root must be a JSON object")
    for key in ("docker_inventory_schema_version", "root", "containers", "images", "volumes"):
        if key not in payload:
            raise DockerPlanError(f"docker inventory missing required field: {key}")
    return payload, sha256


def _container_entry(record: dict[str, Any]) -> dict[str, Any]:
    stopped = str(record.get("state", "")).lower() in _STOPPED_STATES
    linked = bool(record.get("linked_to_workspace"))
    if stopped and linked:
        action = "REVIEW_REQUIRED"
        reason = "stopped container from this workspace; user may review `docker rm` manually"
    else:
        action = "NO_ACTION"
        reason = "running or not linked to this workspace"
    return {
        "object_type": "container",
        "id": record.get("id"),
        "name": record.get("name"),
        "detail": record.get("status"),
        "linked_to_workspace": linked,
        "proposed_action": action,
        "reason": reason,
    }


def _image_entry(record: dict[str, Any]) -> dict[str, Any]:
    dangling = bool(record.get("dangling"))
    return {
        "object_type": "image",
        "id": record.get("id"),
        "name": f"{record.get('repository')}:{record.get('tag')}",
        "detail": record.get("size"),
        "linked_to_workspace": False,
        "proposed_action": "REVIEW_REQUIRED" if dangling else "NO_ACTION",
        "reason": (
            "dangling image; user may review `docker image prune` manually"
            if dangling
            else "tagged image; not a cleanup candidate"
        ),
    }


def _volume_entry(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_type": "volume",
        "id": record.get("name"),
        "name": record.get("name"),
        "detail": record.get("driver"),
        "linked_to_workspace": bool(record.get("linked_to_workspace")),
        "proposed_action": "FORBIDDEN_DEFAULT",
        "reason": "volumes may hold irreplaceable data; never proposed for deletion by default",
    }


def build_docker_plan(docker_inventory: str | Path) -> dict[str, Any]:
    """Build the informational docker cleanup plan payload."""

    inventory_path = Path(docker_inventory).expanduser()
    if not inventory_path.is_file():
        raise DockerPlanError(f"docker inventory not found: {inventory_path}")
    inventory_path = inventory_path.resolve(strict=True)

    inventory, sha256 = _load_inventory(inventory_path)

    entries: list[dict[str, Any]] = []
    entries.extend(_container_entry(record) for record in inventory["containers"])
    entries.extend(_image_entry(record) for record in inventory["images"])
    entries.extend(_volume_entry(record) for record in inventory["volumes"])

    actions = [entry["proposed_action"] for entry in entries]
    return {
        "docker_plan_schema_version": DOCKER_PLAN_SCHEMA_VERSION,
        "plan_id": str(uuid.uuid4()),
        "generated_at_utc": _utc_now(),
        "mode": "DOCKER_PLAN_INFORMATIONAL_ONLY",
        "root": inventory["root"],
        "source_docker_inventory": {
            "path": str(inventory_path),
            "schema_version": inventory["docker_inventory_schema_version"],
            "sha256": sha256,
        },
        "entries": entries,
        "summary": {
            "total_entries": len(entries),
            "review_required": actions.count("REVIEW_REQUIRED"),
            "no_action": actions.count("NO_ACTION"),
            "forbidden_default": actions.count("FORBIDDEN_DEFAULT"),
            "volumes_proposed_for_deletion": 0,
        },
        "safety": {
            "docker_mutation_performed": False,
            "tool_can_execute_this_plan": False,
        },
        "plan_hash": None,
    }
