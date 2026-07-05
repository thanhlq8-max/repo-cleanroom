"""Render clean_report.md from a clean action-log payload.

The report states plainly what was removed, what was not, and that no rollback
exists. It must never claim more recovery capability than implemented (none).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_NON_SUCCESS_DECISIONS = (
    "SKIPPED_CHANGED",
    "SKIPPED_PROTECTED",
    "SKIPPED_GUARD_FAIL",
    "ERROR",
    "NOT_PROCESSED",
)


def render_clean_report(result: dict[str, Any]) -> str:
    """Render a human-readable report for one clean (or dry) run."""

    summary = result.get("summary", {})
    dry_run = bool(result.get("dry_run"))

    if dry_run:
        status = "DRY_RUN"
    elif result.get("failed") or summary.get("partial"):
        status = "PARTIAL"
    else:
        status = "COMPLETE"

    lines: list[str] = []
    lines.append("# Repo Cleanroom Clean Report")
    lines.append("")
    lines.append(f"STATUS: {status}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Root: `{result.get('root', 'UNKNOWN')}`")
    lines.append(f"- Plan id: `{result.get('plan_id', 'UNKNOWN')}`")
    lines.append(f"- Dry run: {'YES' if dry_run else 'NO'}")
    lines.append(f"- Removed: {summary.get('removed', 0)} ({summary.get('removed_bytes', 0)} bytes)")
    lines.append(f"- Would remove (dry run): {summary.get('would_remove', 0)}")
    lines.append(
        "- Skipped: "
        f"{summary.get('skipped_changed', 0) + summary.get('skipped_protected', 0) + summary.get('skipped_guard_fail', 0)}"
    )
    lines.append(f"- Errors: {summary.get('errors', 0)}")
    lines.append(f"- Not processed (stopped after error): {summary.get('not_processed', 0)}")
    lines.append("")

    exceptions = [
        record
        for record in result.get("entries", [])
        if record.get("decision") in _NON_SUCCESS_DECISIONS
    ]
    if exceptions:
        lines.append("## Entries that were not removed")
        lines.append("")
        lines.append("| Entry | Decision | Reason |")
        lines.append("|---|---|---|")
        for record in exceptions:
            lines.append(
                f"| `{record.get('entry_id')}` | {record.get('decision')} | {record.get('reason')} |"
            )
        lines.append("")

    lines.append("## Recovery policy")
    lines.append("")
    lines.append("- There is NO rollback. Removed entries are gone; regenerate them with your build tools.")
    lines.append("- Skipped and not-processed entries remain untouched on disk.")
    lines.append("- A partially executed plan cannot be resumed: rescan, replan, and reapprove.")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_clean_report(path: str | Path, result: dict[str, Any]) -> None:
    """Write clean_report.md."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_clean_report(result), encoding="utf-8")
