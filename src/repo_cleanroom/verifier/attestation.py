"""Build attestation.json and final_report.md from plan + action log + verify results.

An attestation is a factual record of what one approved plan did, cross-checked by
verification. It separates entries into: cleaned, skipped, failed, blocked, unchanged.
It is only issued when verification passed; it never claims more than the logs prove.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ATTESTATION_SCHEMA_VERSION = "0.4.0"

STATUS_ATTESTED = "ATTESTED"
STATUS_ATTESTED_DRY_RUN = "ATTESTED_DRY_RUN"
STATUS_NOT_ATTESTED = "NOT_ATTESTED_VERIFICATION_FAILED"

_SKIP_DECISIONS = {"SKIPPED_CHANGED", "SKIPPED_PROTECTED", "SKIPPED_GUARD_FAIL", "NOT_PROCESSED"}


class AttestationError(ValueError):
    """Raised when attestation inputs are inconsistent."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _categorize(record: dict[str, Any]) -> str:
    decision = record.get("decision", "UNKNOWN")
    if decision == "REMOVED":
        return "cleaned"
    if decision in _SKIP_DECISIONS:
        return "skipped"
    if decision == "ERROR":
        return "failed"
    if decision == "NOT_PROPOSED" and record.get("proposed_action") == "FORBIDDEN":
        return "blocked"
    # NOT_PROPOSED (REVIEW/DANGEROUS/NO_ACTION) and DRY_RUN_WOULD_REMOVE.
    return "unchanged"


def build_attestation_payload(
    plan: dict[str, Any],
    action_log: dict[str, Any],
    verify_payload: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the attestation. Raises AttestationError on inconsistent inputs."""

    plan_id = plan.get("plan_id")
    if action_log.get("plan_id") != plan_id:
        raise AttestationError("action log plan_id does not match the plan")
    if verify_payload.get("plan_id") != plan_id:
        raise AttestationError("verify payload plan_id does not match the plan")

    categories: dict[str, list[dict[str, Any]]] = {
        "cleaned": [],
        "skipped": [],
        "failed": [],
        "blocked": [],
        "unchanged": [],
    }
    for record in action_log.get("entries", []):
        categories[_categorize(record)].append(
            {
                "entry_id": record.get("entry_id"),
                "risk": record.get("risk"),
                "decision": record.get("decision"),
                "reason": record.get("reason"),
            }
        )

    verified = bool(verify_payload.get("summary", {}).get("verified"))
    dry_run = bool(action_log.get("dry_run"))
    if not verified:
        status = STATUS_NOT_ATTESTED
    elif dry_run:
        status = STATUS_ATTESTED_DRY_RUN
    else:
        status = STATUS_ATTESTED

    return {
        "attestation_schema_version": ATTESTATION_SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "status": status,
        "root": plan.get("root"),
        "plan_id": plan_id,
        "dry_run": dry_run,
        "verification": {
            "verified": verified,
            "summary": verify_payload.get("summary", {}),
        },
        "categories": categories,
        "counts": {name: len(items) for name, items in categories.items()},
        "removed_bytes": action_log.get("summary", {}).get("removed_bytes", 0),
    }


def render_final_report(attestation: dict[str, Any]) -> str:
    """Render final_report.md from an attestation payload."""

    counts = attestation.get("counts", {})
    lines: list[str] = []
    lines.append("# Repo Cleanroom Final Report")
    lines.append("")
    lines.append(f"STATUS: {attestation.get('status')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Root: `{attestation.get('root', 'UNKNOWN')}`")
    lines.append(f"- Plan id: `{attestation.get('plan_id', 'UNKNOWN')}`")
    lines.append(f"- Dry run: {'YES' if attestation.get('dry_run') else 'NO'}")
    lines.append(
        f"- Verified against filesystem: "
        f"{'YES' if attestation.get('verification', {}).get('verified') else 'NO'}"
    )
    lines.append(f"- Removed bytes: {attestation.get('removed_bytes', 0)}")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    for name in ("cleaned", "skipped", "failed", "blocked", "unchanged"):
        lines.append(f"| {name} | {counts.get(name, 0)} |")
    lines.append("")

    for name, heading in (
        ("cleaned", "Cleaned (removed per approved plan, absence verified)"),
        ("skipped", "Skipped (guards or fail-fast; still on disk)"),
        ("failed", "Failed (removal error)"),
        ("blocked", "Blocked (protected; never removable)"),
        ("unchanged", "Unchanged (never in removal scope)"),
    ):
        items = attestation.get("categories", {}).get(name, [])
        if not items:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        lines.append("| Entry | Risk | Decision | Reason |")
        lines.append("|---|---|---|---|")
        for item in items:
            lines.append(
                f"| `{item.get('entry_id')}` | {item.get('risk')} | "
                f"{item.get('decision')} | {item.get('reason')} |"
            )
        lines.append("")

    lines.append("## Scope notes")
    lines.append("")
    lines.append("- This attestation covers only the entries of the plan named above.")
    lines.append("- It makes no claim about any other file, directory, or system state.")
    lines.append("- There is NO rollback for cleaned entries.")
    if attestation.get("status") == STATUS_NOT_ATTESTED:
        lines.append("- VERIFICATION FAILED: this document attests the discrepancy, not a clean state.")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_final_report(path: str | Path, attestation: dict[str, Any]) -> None:
    """Write final_report.md."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_final_report(attestation), encoding="utf-8")
