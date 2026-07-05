"""Build verify.json from a plan, its clean action log, and the live filesystem.

For every plan entry the verifier derives the expected post-clean state from the
action-log decision and compares it against the filesystem:

- REMOVED            -> expected ABSENT  (still present = FAIL_STILL_PRESENT)
- SKIPPED_CHANGED    -> expected ANY     (state was already indeterminate at clean time)
- everything else    -> expected PRESENT (missing = FAIL_MISSING)

FAIL_MISSING on a non-removed entry is the critical signal: something outside the
approved plan deleted data. The verifier itself is read-only.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERIFY_SCHEMA_VERSION = "0.4.0"

RESULT_OK = "OK"
RESULT_FAIL_STILL_PRESENT = "FAIL_STILL_PRESENT"
RESULT_FAIL_MISSING = "FAIL_MISSING"

EXPECTED_ABSENT = "ABSENT"
EXPECTED_PRESENT = "PRESENT"
EXPECTED_ANY = "ANY"


class VerifyError(ValueError):
    """Raised when verification inputs are inconsistent and no verdict is possible."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest of a file's bytes."""

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _expected_state(decision: str) -> str:
    if decision == "REMOVED":
        return EXPECTED_ABSENT
    if decision == "SKIPPED_CHANGED":
        return EXPECTED_ANY
    return EXPECTED_PRESENT


def _check_inside_root(root: Path, candidate: str) -> None:
    resolved = Path(candidate).expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise VerifyError(f"plan entry path escapes root: {resolved}") from exc


def build_verify_payload(
    plan: dict[str, Any],
    action_log: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Compare filesystem state against the plan + action log. Read-only."""

    if plan.get("plan_id") != action_log.get("plan_id"):
        raise VerifyError("action log plan_id does not match the plan")
    if str(Path(str(plan.get("root"))).resolve()) != str(root.resolve()):
        raise VerifyError("plan root does not match the requested verify root")
    if str(Path(str(action_log.get("root"))).resolve()) != str(root.resolve()):
        raise VerifyError("action log root does not match the requested verify root")

    log_by_entry = {record.get("entry_id"): record for record in action_log.get("entries", [])}

    results: list[dict[str, Any]] = []
    counts = {RESULT_OK: 0, RESULT_FAIL_STILL_PRESENT: 0, RESULT_FAIL_MISSING: 0}

    for entry in plan.get("entries", []):
        entry_id = entry.get("entry_id")
        record = log_by_entry.get(entry_id)
        if record is None:
            raise VerifyError(f"action log has no record for plan entry: {entry_id}")

        _check_inside_root(root, entry["path"])

        decision = record.get("decision", "UNKNOWN")
        expected = _expected_state(decision)
        # lexists: a dangling symlink still counts as present on disk.
        actual = EXPECTED_PRESENT if os.path.lexists(entry["path"]) else EXPECTED_ABSENT

        if expected == EXPECTED_ANY or expected == actual:
            result = RESULT_OK
        elif expected == EXPECTED_ABSENT:
            result = RESULT_FAIL_STILL_PRESENT
        else:
            result = RESULT_FAIL_MISSING
        counts[result] += 1

        results.append(
            {
                "entry_id": entry_id,
                "path": entry.get("path"),
                "risk": entry.get("risk"),
                "proposed_action": entry.get("proposed_action"),
                "log_decision": decision,
                "expected": expected,
                "actual": actual,
                "result": result,
            }
        )

    verified = counts[RESULT_FAIL_STILL_PRESENT] == 0 and counts[RESULT_FAIL_MISSING] == 0
    return {
        "verify_schema_version": VERIFY_SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "mode": "READ_ONLY_VERIFY",
        "root": str(root),
        "plan_id": plan.get("plan_id"),
        "action_log_mode": action_log.get("mode"),
        "action_log_dry_run": bool(action_log.get("dry_run")),
        "entries": results,
        "summary": {
            "total_entries": len(results),
            "ok": counts[RESULT_OK],
            "fail_still_present": counts[RESULT_FAIL_STILL_PRESENT],
            "fail_missing": counts[RESULT_FAIL_MISSING],
            "verified": verified,
        },
    }
