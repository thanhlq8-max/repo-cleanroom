"""Approval token issuance and verification.

Implements docs/APPROVAL_TOKEN.md. A token binds one human approval to one
byte-exact plan via the canonical plan hash. Any plan mutation invalidates it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.planners.plan_hash import compute_plan_hash

TOKEN_SCHEMA_VERSION = "0.2.0"

APPROVED_ACTION = "REMOVE_PROPOSED_SAFE"

APPROVED_RISK_CLASSES = ["SAFE"]

EXPIRY_HOURS = 24

_REQUIRED_TOKEN_FIELDS = (
    "token_schema_version",
    "plan_id",
    "plan_hash",
    "root",
    "entry_count",
    "approved_action",
    "approved_risk_classes",
    "approved_remove_count",
    "approved_remove_bytes",
    "approved_at_utc",
    "expires_at_utc",
    "approved_by",
)


class ApprovalError(ValueError):
    """Raised when a token cannot be issued or fails verification."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ApprovalError(f"token field {field} is not a valid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ApprovalError(f"token field {field} must carry a UTC offset")
    return parsed


def build_approval_token(plan: dict[str, Any], approved_by: str) -> dict[str, Any]:
    """Issue an approval token bound to the exact plan payload."""

    if not approved_by or not approved_by.strip():
        raise ApprovalError("approved_by must not be empty")
    if plan.get("mode") != "PLAN_ONLY":
        raise ApprovalError("only PLAN_ONLY plans can be approved")
    summary = plan.get("summary")
    if not isinstance(summary, dict):
        raise ApprovalError("plan has no summary; cannot approve")
    for key in ("total_entries", "proposed_remove_count", "proposed_remove_bytes"):
        if key not in summary:
            raise ApprovalError(f"plan summary missing required field: {key}")

    approved_at = _utc_now()
    return {
        "token_schema_version": TOKEN_SCHEMA_VERSION,
        "plan_id": plan.get("plan_id", "UNKNOWN"),
        "plan_hash": compute_plan_hash(plan),
        "root": plan.get("root"),
        "entry_count": summary["total_entries"],
        "approved_action": APPROVED_ACTION,
        "approved_risk_classes": list(APPROVED_RISK_CLASSES),
        "approved_remove_count": summary["proposed_remove_count"],
        "approved_remove_bytes": summary["proposed_remove_bytes"],
        "approved_at_utc": approved_at.isoformat(),
        "expires_at_utc": (approved_at + timedelta(hours=EXPIRY_HOURS)).isoformat(),
        "approved_by": approved_by.strip(),
    }


def verify_approval_token(token: dict[str, Any], plan: dict[str, Any], root: Path) -> None:
    """Apply every verification rule from docs/APPROVAL_TOKEN.md section 4.

    Raises ApprovalError naming the first failed rule. Passing means the token
    approves exactly this plan for exactly this root, right now.
    """

    for field in _REQUIRED_TOKEN_FIELDS:
        if field not in token:
            raise ApprovalError(f"token missing required field: {field}")

    if token["token_schema_version"] != TOKEN_SCHEMA_VERSION:
        raise ApprovalError(
            f"unsupported token schema version: {token['token_schema_version']!r}"
        )

    actual_hash = compute_plan_hash(plan)
    if token["plan_hash"] != actual_hash:
        raise ApprovalError("plan hash mismatch: the plan changed after approval")

    plan_root = plan.get("root")
    if token["root"] != plan_root:
        raise ApprovalError("token root does not match plan root")
    if Path(plan_root).resolve() != Path(root).resolve():
        raise ApprovalError("plan root does not match the requested clean root")

    summary = plan.get("summary", {})
    if token["entry_count"] != summary.get("total_entries"):
        raise ApprovalError("token entry_count does not match plan summary")
    if token["approved_remove_count"] != summary.get("proposed_remove_count"):
        raise ApprovalError("token approved_remove_count does not match plan summary")
    if token["approved_remove_bytes"] != summary.get("proposed_remove_bytes"):
        raise ApprovalError("token approved_remove_bytes does not match plan summary")

    if token["approved_action"] != APPROVED_ACTION:
        raise ApprovalError("token approved_action is not REMOVE_PROPOSED_SAFE")
    if token["approved_risk_classes"] != APPROVED_RISK_CLASSES:
        raise ApprovalError("token approved_risk_classes must be exactly ['SAFE']")

    expires_at = _parse_utc(token["expires_at_utc"], "expires_at_utc")
    if _utc_now() >= expires_at:
        raise ApprovalError("approval token has expired; rescan, replan, and reapprove")
