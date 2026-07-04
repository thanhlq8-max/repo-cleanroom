"""Markdown report rendering."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


MAX_LARGEST_ARTIFACTS = 10

RISK_ORDER = ["SAFE", "REVIEW", "DANGEROUS", "BLOCKED"]


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def _artifact_display_path(item: dict[str, Any]) -> str:
    """Return the repo-local display path for an artifact finding."""

    repo_rel = item.get("repo_relative_path", "")
    artifact_rel = item.get("relative_path", "")
    return f"{repo_rel}/{artifact_rel}" if repo_rel else artifact_rel


def _artifact_size(item: dict[str, Any]) -> int:
    """Return artifact size as an integer for sorting/reporting."""

    try:
        return int(item.get("size_bytes", 0))
    except (TypeError, ValueError):
        return 0


def render_findings_markdown(inventory: dict[str, Any], artifact_inventory: dict[str, Any]) -> str:
    """Render findings as Markdown."""

    repos = inventory.get("repos", [])
    artifacts = artifact_inventory.get("artifacts", [])
    risk_counts = Counter(item.get("risk", "UNKNOWN") for item in artifacts)
    total_size = sum(_artifact_size(item) for item in artifacts)

    lines: list[str] = []
    lines.append("# Repo Cleanroom Findings")
    lines.append("")
    lines.append("STATUS: READ_ONLY_SCAN_COMPLETE")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Root: `{inventory.get('root', 'UNKNOWN')}`")
    lines.append(f"- Repositories scanned: {len(repos)}")
    lines.append(f"- Artifacts found: {len(artifacts)}")
    lines.append(f"- Estimated artifact size: {_format_bytes(total_size)}")
    lines.append("- Cleanup performed: NO")
    lines.append("- Shell history read: NO")
    lines.append("- Target repo scripts executed: NO")
    lines.append("")
    lines.append("## Risk counts")
    lines.append("")
    lines.append("| Risk | Count |")
    lines.append("|---|---:|")
    for risk in ["SAFE", "REVIEW", "DANGEROUS", "BLOCKED"]:
        lines.append(f"| {risk} | {risk_counts.get(risk, 0)} |")
    lines.append("")
    lines.append("## Largest artifacts")
    lines.append("")
    if not artifacts:
        lines.append("No known repo-local artifacts were detected.")
    else:
        lines.append("| Risk | Size | Repo-local path | Type |")
        lines.append("|---|---:|---|---|")
        largest = sorted(artifacts, key=_artifact_size, reverse=True)[:MAX_LARGEST_ARTIFACTS]
        for item in largest:
            lines.append(
                f"| {item.get('risk')} | {_format_bytes(_artifact_size(item))} | "
                f"`{_artifact_display_path(item)}` | `{item.get('artifact_type')}` |"
            )
    lines.append("")
    lines.append("## Repositories")
    lines.append("")
    if not repos:
        lines.append("No Git repositories were discovered under the selected root.")
    else:
        lines.append("| Repo | Relative path | Manifests |")
        lines.append("|---|---|---:|")
        manifest_counts = Counter(item.get("repo_path") for item in inventory.get("manifests", []))
        for repo in repos:
            lines.append(
                f"| `{repo.get('name')}` | `{repo.get('relative_path')}` | {manifest_counts.get(repo.get('path'), 0)} |"
            )
    lines.append("")
    lines.append("## Artifact findings by risk")
    lines.append("")
    if not artifacts:
        lines.append("No known repo-local artifacts were detected.")
        lines.append("")
    else:
        known_risks = set(RISK_ORDER)
        other_risks = sorted({item.get("risk", "UNKNOWN") for item in artifacts} - known_risks)
        for risk in RISK_ORDER + other_risks:
            group = [item for item in artifacts if item.get("risk", "UNKNOWN") == risk]
            if not group:
                continue
            group_size = sum(_artifact_size(item) for item in group)
            lines.append(f"### {risk} ({len(group)} finding(s), {_format_bytes(group_size)})")
            lines.append("")
            lines.append("| Type | Size | Repo-local path | Reason |")
            lines.append("|---|---:|---|---|")
            for item in sorted(group, key=_artifact_size, reverse=True):
                lines.append(
                    f"| `{item.get('artifact_type')}` | {_format_bytes(_artifact_size(item))} | "
                    f"`{_artifact_display_path(item)}` | {item.get('reason')} |"
                )
            lines.append("")
    lines.append("## Safety notes")
    lines.append("")
    lines.append("- v0.1.0 is read-only and does not remove files.")
    lines.append("- Detection does not equal removal approval.")
    lines.append("- `BLOCKED` items must not be automatically removed or printed as content.")
    lines.append("- Symlink targets are not traversed for size estimation.")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_findings_markdown(path: str | Path, inventory: dict[str, Any], artifact_inventory: dict[str, Any]) -> None:
    """Write findings markdown."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_findings_markdown(inventory, artifact_inventory), encoding="utf-8")
