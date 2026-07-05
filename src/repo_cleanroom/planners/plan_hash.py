"""Canonical plan hashing.

Implements the plan_hash definition locked in docs/CLEANUP_PLAN_SCHEMA.md section 5:
SHA-256 hex digest of the plan JSON serialized canonically (UTF-8, sorted keys,
plan_hash field set to null, no insignificant whitespace).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class PlanHashError(ValueError):
    """Raised when a plan file cannot be loaded for hashing."""


def compute_plan_hash(plan: dict[str, Any]) -> str:
    """Return the canonical SHA-256 hex digest for a plan payload."""

    payload = dict(plan)
    payload["plan_hash"] = None
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_plan_file(path: str | Path) -> dict[str, Any]:
    """Load a cleanup_plan.json file for hashing/verification."""

    plan_path = Path(path).expanduser()
    if not plan_path.is_file():
        raise PlanHashError(f"plan file not found: {plan_path}")
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlanHashError(f"plan file is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlanHashError("plan file root must be a JSON object")
    return payload
