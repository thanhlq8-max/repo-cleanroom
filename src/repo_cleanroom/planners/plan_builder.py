"""Build cleanup_plan.json payloads from an existing artifact inventory.

A plan is a reviewable proposal document. It is data, not permission.
Plan generation must never remove, move, or modify scanned files.
See docs/CLEANUP_PLAN_SCHEMA.md (v0.2.0-A design).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.safety.path_guard import ensure_within_root, resolve_existing_directory

PLAN_SCHEMA_VERSION = "0.2.0"

PLAN_MODE = "PLAN_ONLY"

_REQUIRED_ARTIFACT_FIELDS = (
    "repo_name",
    "repo_relative_path",
    "relative_path",
    "path",
    "artifact_type",
    "risk",
    "size_bytes",
    "file_count",
    "is_symlink",
)

_ACTION_BY_RISK = {
    "SAFE": "PROPOSE_REMOVE",
    "REVIEW": "REVIEW_REQUIRED",
    "DANGEROUS": "NO_ACTION",
    "BLOCKED": "FORBIDDEN",
}

_REASON_BY_ACTION = {
    "PROPOSE_REMOVE": "SAFE repo-local generated artifact; candidate for future approved clean",
    "REVIEW_REQUIRED": "may contain user/runtime data; manual inspection required",
    "NO_ACTION": "excluded from proposals in v0.2.x",
    "FORBIDDEN": "protected sensitive path/name pattern; must never be removed or printed",
}


class PlanBuildError(ValueError):
    """Raised when the source inventory cannot produce a complete valid plan."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_inventory(scan_artifacts_path: Path) -> tuple[dict[str, Any], str]:
    raw = scan_artifacts_path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlanBuildError(f"artifact inventory is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlanBuildError("artifact inventory root must be a JSON object")
    for key in ("schema_version", "root", "artifacts"):
        if key not in payload:
            raise PlanBuildError(f"artifact inventory missing required field: {key}")
    if not isinstance(payload["artifacts"], list):
        raise PlanBuildError("artifact inventory field 'artifacts' must be a list")
    return payload, sha256


def _proposed_action(risk: str, is_symlink: bool) -> str:
    if risk not in _ACTION_BY_RISK:
        raise PlanBuildError(f"unknown risk class in inventory: {risk!r}")
    if risk == "SAFE" and is_symlink:
        return "NO_ACTION"
    return _ACTION_BY_RISK[risk]


def _entry_reason(action: str, risk: str, is_symlink: bool) -> str:
    if action == "NO_ACTION" and risk == "SAFE" and is_symlink:
        return "symlinked artifacts are never proposed for removal"
    return _REASON_BY_ACTION[action]


def _build_entry(record: dict[str, Any], root: Path) -> dict[str, Any]:
    for field in _REQUIRED_ARTIFACT_FIELDS:
        if field not in record:
            raise PlanBuildError(f"artifact record missing required field: {field}")

    # Re-check the root boundary at plan time; a failing path aborts the whole plan.
    ensure_within_root(root, record["path"])

    risk = str(record["risk"])
    is_symlink = bool(record["is_symlink"])
    action = _proposed_action(risk, is_symlink)

    return {
        "entry_id": f"{record['repo_relative_path']}/{record['relative_path']}",
        "repo_name": record["repo_name"],
        "repo_relative_path": record["repo_relative_path"],
        "relative_path": record["relative_path"],
        "path": record["path"],
        "artifact_type": record["artifact_type"],
        "risk": risk,
        "size_bytes": int(record["size_bytes"]),
        "file_count": int(record["file_count"]),
        "is_symlink": is_symlink,
        "proposed_action": action,
        "reason": _entry_reason(action, risk, is_symlink),
    }


def build_plan_payload(scan_artifacts: str | Path) -> dict[str, Any]:
    """Build a complete PLAN_ONLY payload from an artifact_inventory.json file."""

    scan_artifacts_path = Path(scan_artifacts).expanduser()
    if not scan_artifacts_path.is_file():
        raise PlanBuildError(f"artifact inventory not found: {scan_artifacts_path}")
    scan_artifacts_path = scan_artifacts_path.resolve(strict=True)

    inventory, inventory_sha256 = _load_inventory(scan_artifacts_path)
    root = resolve_existing_directory(inventory["root"])

    entries = [_build_entry(record, root) for record in inventory["artifacts"]]

    proposed = [item for item in entries if item["proposed_action"] == "PROPOSE_REMOVE"]
    risk_counts: dict[str, int] = {}
    for item in entries:
        risk_counts[item["risk"]] = risk_counts.get(item["risk"], 0) + 1

    return {
        "plan_id": str(uuid.uuid4()),
        "plan_schema_version": PLAN_SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "mode": PLAN_MODE,
        "root": str(root),
        "source_artifact_inventory": {
            "path": str(scan_artifacts_path),
            "schema_version": inventory["schema_version"],
            "sha256": inventory_sha256,
        },
        "entries": entries,
        "summary": {
            "total_entries": len(entries),
            "proposed_remove_count": len(proposed),
            "proposed_remove_bytes": sum(item["size_bytes"] for item in proposed),
            "review_required_count": sum(
                1 for item in entries if item["proposed_action"] == "REVIEW_REQUIRED"
            ),
            "blocked_count": sum(1 for item in entries if item["proposed_action"] == "FORBIDDEN"),
            "no_action_count": sum(1 for item in entries if item["proposed_action"] == "NO_ACTION"),
            "by_risk": dict(sorted(risk_counts.items())),
        },
        "plan_hash": None,
    }
