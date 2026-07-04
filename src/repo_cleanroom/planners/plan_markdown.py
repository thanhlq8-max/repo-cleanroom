"""Render cleanup_plan.md from a cleanup plan payload.

The rendering is review material only. It must never suggest that generating
or reading a plan removes anything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ACTION_ORDER = ["PROPOSE_REMOVE", "REVIEW_REQUIRED", "FORBIDDEN", "NO_ACTION"]

_ACTION_HEADINGS = {
    "PROPOSE_REMOVE": "Proposed for future approved removal",
    "REVIEW_REQUIRED": "Requires manual review",
    "FORBIDDEN": "Forbidden (protected items)",
    "NO_ACTION": "No action",
}


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def render_plan_markdown(plan: dict[str, Any]) -> str:
    """Render a cleanup plan payload as reviewable Markdown."""

    entries = plan.get("entries", [])
    summary = plan.get("summary", {})

    lines: list[str] = []
    lines.append("# Repo Cleanroom Cleanup Plan (PLAN_ONLY)")
    lines.append("")
    lines.append("STATUS: PLAN_ONLY — this plan is a proposal document. Nothing was deleted.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Plan id: `{plan.get('plan_id', 'UNKNOWN')}`")
    lines.append(f"- Root: `{plan.get('root', 'UNKNOWN')}`")
    lines.append(
        f"- Source inventory: `{plan.get('source_artifact_inventory', {}).get('path', 'UNKNOWN')}`"
    )
    lines.append(f"- Total entries: {summary.get('total_entries', 0)}")
    lines.append(
        f"- Proposed for future removal: {summary.get('proposed_remove_count', 0)} "
        f"({_format_bytes(int(summary.get('proposed_remove_bytes', 0)))})"
    )
    lines.append(f"- Review required: {summary.get('review_required_count', 0)}")
    lines.append(f"- Forbidden (protected): {summary.get('blocked_count', 0)}")
    lines.append(f"- No action: {summary.get('no_action_count', 0)}")
    lines.append("- Files removed by this plan: NONE")
    lines.append("")

    for action in ACTION_ORDER:
        group = [item for item in entries if item.get("proposed_action") == action]
        if not group:
            continue
        group_size = sum(int(item.get("size_bytes", 0)) for item in group)
        lines.append(f"## {_ACTION_HEADINGS[action]} ({len(group)} entry(ies), {_format_bytes(group_size)})")
        lines.append("")
        lines.append("| Risk | Type | Size | Entry | Reason |")
        lines.append("|---|---|---:|---|---|")
        for item in sorted(group, key=lambda record: int(record.get("size_bytes", 0)), reverse=True):
            lines.append(
                f"| {item.get('risk')} | `{item.get('artifact_type')}` | "
                f"{_format_bytes(int(item.get('size_bytes', 0)))} | `{item.get('entry_id')}` | "
                f"{item.get('reason')} |"
            )
        lines.append("")

    lines.append("## Safety notes")
    lines.append("")
    lines.append("- A plan is not permission. No file is removed by generating or reading it.")
    lines.append("- Future removal requires the approval-token flow (docs/APPROVAL_TOKEN.md) in v0.3.x.")
    lines.append("- FORBIDDEN entries must never be removed under any flow.")
    lines.append("- REVIEW_REQUIRED entries are never auto-promoted to removal by the tool.")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_plan_markdown(path: str | Path, plan: dict[str, Any]) -> None:
    """Write cleanup_plan.md."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_plan_markdown(plan), encoding="utf-8")
