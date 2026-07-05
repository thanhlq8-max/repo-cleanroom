"""Guarded execution of an approved cleanup plan.

Implements docs/CLEANER_SAFETY_MODEL.md sections 1, 3, 4, and 5:
only SAFE PROPOSE_REMOVE entries, every guard re-checked at delete time,
one action-log record per plan entry, fail-fast on the first error.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.safety.path_guard import PathGuardError, ensure_within_root
from repo_cleanroom.safety.secret_guard import is_protected_path

# Action-log decisions. NOT_PROPOSED and NOT_PROCESSED extend the design list so the
# log can keep one record per plan entry (design section 4) even for entries the
# prototype never acts on.
DECISION_REMOVED = "REMOVED"
DECISION_DRY_RUN = "DRY_RUN_WOULD_REMOVE"
DECISION_SKIPPED_CHANGED = "SKIPPED_CHANGED"
DECISION_SKIPPED_PROTECTED = "SKIPPED_PROTECTED"
DECISION_SKIPPED_GUARD_FAIL = "SKIPPED_GUARD_FAIL"
DECISION_ERROR = "ERROR"
DECISION_NOT_PROPOSED = "NOT_PROPOSED"
DECISION_NOT_PROCESSED = "NOT_PROCESSED"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _inspect_entry_tree(entry_path: Path) -> tuple[int, int, str | None]:
    """Walk an entry without following symlinks.

    Returns (size_bytes, file_count, refusal_reason). A refusal reason is set when
    a protected name is planted inside the entry or the walk crosses onto another
    filesystem/device (mount or junction boundary).
    """

    if entry_path.is_file():
        if is_protected_path(entry_path):
            return 0, 0, "protected name inside entry"
        stat = entry_path.stat()
        return int(stat.st_size), 1, None

    root_dev = entry_path.stat().st_dev
    size_bytes = 0
    file_count = 0
    for current, dirs, files in os.walk(entry_path, followlinks=False):
        current_path = Path(current)
        if current_path.stat().st_dev != root_dev:
            return size_bytes, file_count, "entry crosses a filesystem boundary"
        for name in list(dirs) + list(files):
            if is_protected_path(name):
                return size_bytes, file_count, "protected name inside entry"
        for name in files:
            child = current_path / name
            file_count += 1
            if not child.is_symlink():
                try:
                    size_bytes += child.stat().st_size
                except OSError:
                    pass
    return size_bytes, file_count, None


def _remove_dir_or_link(path: Path) -> None:
    """Remove a directory entry that may be a symlink/junction, never its target."""

    if path.is_symlink():
        try:
            path.rmdir()
        except OSError:
            path.unlink()
    else:
        path.rmdir()


def _remove_entry_tree(entry_path: Path) -> None:
    """Bottom-up removal without following symlinks."""

    if entry_path.is_file() or entry_path.is_symlink():
        entry_path.unlink()
        return

    for current, dirs, files in os.walk(entry_path, topdown=False, followlinks=False):
        current_path = Path(current)
        for name in files:
            child = current_path / name
            child.unlink()
        for name in dirs:
            _remove_dir_or_link(current_path / name)
    entry_path.rmdir()


def _guard_entry(entry: dict[str, Any], root: Path) -> tuple[str | None, str | None]:
    """Re-check every per-entry guard. Returns (decision, reason) or (None, None)."""

    if entry.get("risk") != "SAFE" or entry.get("is_symlink"):
        return DECISION_SKIPPED_GUARD_FAIL, "entry is not a non-symlink SAFE artifact"

    entry_path = Path(entry["path"])
    if entry_path.is_symlink():
        return DECISION_SKIPPED_CHANGED, "path became a symlink after planning"
    if not entry_path.exists():
        return DECISION_SKIPPED_CHANGED, "path no longer exists"

    try:
        resolved = ensure_within_root(root, entry_path)
    except PathGuardError as exc:
        return DECISION_SKIPPED_GUARD_FAIL, str(exc)

    if ".git" in resolved.parts:
        return DECISION_SKIPPED_GUARD_FAIL, "entry touches a .git component"
    if is_protected_path(resolved):
        return DECISION_SKIPPED_PROTECTED, "entry path matches a protected pattern"
    return None, None


def execute_clean(plan: dict[str, Any], root: Path, dry_run: bool) -> dict[str, Any]:
    """Execute (or dry-run) the PROPOSE_REMOVE entries of a verified plan.

    Returns the action-log payload. The caller is responsible for having verified
    the approval token before calling this function.
    """

    records: list[dict[str, Any]] = []
    removed_paths: list[str] = []
    removed_bytes = 0
    failed = False

    for entry in plan.get("entries", []):
        record: dict[str, Any] = {
            "entry_id": entry.get("entry_id"),
            "path": entry.get("path"),
            "risk": entry.get("risk"),
            "proposed_action": entry.get("proposed_action"),
            "timestamp_utc": _utc_now(),
        }
        records.append(record)

        if entry.get("proposed_action") != "PROPOSE_REMOVE":
            record["decision"] = DECISION_NOT_PROPOSED
            record["reason"] = "entry was never in the approved removal scope"
            continue

        if failed:
            record["decision"] = DECISION_NOT_PROCESSED
            record["reason"] = "run stopped after an earlier error (fail-fast)"
            continue

        decision, reason = _guard_entry(entry, root)
        if decision is not None:
            record["decision"] = decision
            record["reason"] = reason
            continue

        entry_path = Path(entry["path"])
        try:
            size_bytes, file_count, refusal = _inspect_entry_tree(entry_path)
            record["observed_size_bytes"] = size_bytes
            record["observed_file_count"] = file_count
            if refusal is not None:
                record["decision"] = (
                    DECISION_SKIPPED_PROTECTED
                    if "protected" in refusal
                    else DECISION_SKIPPED_GUARD_FAIL
                )
                record["reason"] = refusal
                continue

            if dry_run:
                record["decision"] = DECISION_DRY_RUN
                record["reason"] = "dry run: nothing removed"
                continue

            _remove_entry_tree(entry_path)
            record["decision"] = DECISION_REMOVED
            record["reason"] = "removed per approved plan"
            removed_paths.append(str(entry_path))
            removed_bytes += size_bytes
        except OSError as exc:
            record["decision"] = DECISION_ERROR
            record["reason"] = f"{exc.__class__.__name__}: {exc}"
            failed = True

    decisions = [record["decision"] for record in records]

    return {
        "log_schema_version": "0.3.0",
        "generated_at_utc": _utc_now(),
        "mode": "CLEAN_DRY_RUN" if dry_run else "CLEAN_EXECUTE",
        "root": str(root),
        "plan_id": plan.get("plan_id"),
        "dry_run": dry_run,
        "failed": failed,
        "entries": records,
        "summary": {
            "total_records": len(records),
            "removed": decisions.count(DECISION_REMOVED),
            "would_remove": decisions.count(DECISION_DRY_RUN),
            "skipped_changed": decisions.count(DECISION_SKIPPED_CHANGED),
            "skipped_protected": decisions.count(DECISION_SKIPPED_PROTECTED),
            "skipped_guard_fail": decisions.count(DECISION_SKIPPED_GUARD_FAIL),
            "errors": decisions.count(DECISION_ERROR),
            "not_processed": decisions.count(DECISION_NOT_PROCESSED),
            "not_proposed": decisions.count(DECISION_NOT_PROPOSED),
            "removed_bytes": removed_bytes,

        },
        "removed_paths": removed_paths,
    }
