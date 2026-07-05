"""Static HTML rendering of scan findings.

The output is a single self-contained file: inline CSS, no JavaScript, no
external resources. Every value from the scanned workspace (repo names, paths,
types, reasons) is HTML-escaped — scanned repositories are untrusted input and
must not be able to inject markup into the review page.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

RISK_ORDER = ["SAFE", "REVIEW", "DANGEROUS", "BLOCKED"]

_STYLE = """
body { font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; margin: 2rem auto;
       max-width: 60rem; padding: 0 1rem; color: #1a1a1a; }
h1, h2 { border-bottom: 1px solid #ddd; padding-bottom: .3rem; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0 1.5rem; }
th, td { border: 1px solid #ddd; padding: .4rem .6rem; text-align: left;
         font-size: .92rem; word-break: break-all; }
th { background: #f5f5f5; }
td.num { text-align: right; white-space: nowrap; }
code { background: #f5f5f5; padding: .1rem .3rem; border-radius: 3px; }
.badge { display: inline-block; padding: .1rem .5rem; border-radius: 3px;
         font-size: .85rem; font-weight: 600; }
.badge-SAFE { background: #e6f4ea; color: #1e7e34; }
.badge-REVIEW { background: #fff3cd; color: #856404; }
.badge-DANGEROUS { background: #fde2e1; color: #b02a37; }
.badge-BLOCKED { background: #e2e3e5; color: #383d41; }
.note { background: #f0f4f8; border-left: 4px solid #4a90d9; padding: .6rem 1rem;
        margin: 1rem 0; }
"""


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def _artifact_size(item: dict[str, Any]) -> int:
    try:
        return int(item.get("size_bytes", 0))
    except (TypeError, ValueError):
        return 0


def _display_path(item: dict[str, Any]) -> str:
    repo_rel = item.get("repo_relative_path", "")
    artifact_rel = item.get("relative_path", "")
    return f"{repo_rel}/{artifact_rel}" if repo_rel else str(artifact_rel)


def _badge(risk: str) -> str:
    safe_risk = escape(str(risk))
    css = safe_risk if safe_risk in RISK_ORDER else "BLOCKED"
    return f'<span class="badge badge-{css}">{safe_risk}</span>'


def render_findings_html(inventory: dict[str, Any], artifact_inventory: dict[str, Any]) -> str:
    """Render the findings review page as one self-contained HTML document."""

    repos = inventory.get("repos", [])
    artifacts = artifact_inventory.get("artifacts", [])
    total_size = sum(_artifact_size(item) for item in artifacts)

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append("<title>Repo Cleanroom Findings</title>")
    parts.append(f"<style>{_STYLE}</style></head><body>")
    parts.append("<h1>Repo Cleanroom Findings</h1>")
    parts.append("<p><strong>STATUS: READ_ONLY_SCAN_COMPLETE</strong></p>")

    parts.append("<h2>Summary</h2><table>")
    rows = [
        ("Root", f"<code>{escape(str(inventory.get('root', 'UNKNOWN')))}</code>"),
        ("Repositories scanned", str(len(repos))),
        ("Artifacts found", str(len(artifacts))),
        ("Estimated artifact size", escape(_format_bytes(total_size))),
        ("Cleanup performed", "NO"),
        ("Shell history read", "NO"),
        ("Target repo scripts executed", "NO"),
    ]
    for label, value in rows:
        parts.append(f"<tr><th>{label}</th><td>{value}</td></tr>")
    parts.append("</table>")

    parts.append("<h2>Findings by risk</h2>")
    if not artifacts:
        parts.append("<p>No known repo-local artifacts were detected.</p>")
    else:
        known = set(RISK_ORDER)
        other = sorted({str(item.get("risk", "UNKNOWN")) for item in artifacts} - known)
        for risk in RISK_ORDER + other:
            group = [item for item in artifacts if str(item.get("risk", "UNKNOWN")) == risk]
            if not group:
                continue
            group_size = sum(_artifact_size(item) for item in group)
            parts.append(
                f"<h3>{_badge(risk)} {len(group)} finding(s), "
                f"{escape(_format_bytes(group_size))}</h3>"
            )
            parts.append(
                "<table><tr><th>Type</th><th>Size</th><th>Repo-local path</th><th>Reason</th></tr>"
            )
            for item in sorted(group, key=_artifact_size, reverse=True):
                parts.append(
                    "<tr>"
                    f"<td><code>{escape(str(item.get('artifact_type')))}</code></td>"
                    f'<td class="num">{escape(_format_bytes(_artifact_size(item)))}</td>'
                    f"<td><code>{escape(_display_path(item))}</code></td>"
                    f"<td>{escape(str(item.get('reason')))}</td>"
                    "</tr>"
                )
            parts.append("</table>")

    parts.append("<h2>Repositories</h2>")
    if not repos:
        parts.append("<p>No Git repositories were discovered under the selected root.</p>")
    else:
        parts.append("<table><tr><th>Repo</th><th>Relative path</th></tr>")
        for repo in repos:
            parts.append(
                "<tr>"
                f"<td><code>{escape(str(repo.get('name')))}</code></td>"
                f"<td><code>{escape(str(repo.get('relative_path')))}</code></td>"
                "</tr>"
            )
        parts.append("</table>")

    parts.append(
        '<div class="note"><strong>Safety notes.</strong> '
        "This report is read-only evidence: nothing was removed. Detection does not equal "
        "removal approval. BLOCKED items must never be auto-removed or printed as content. "
        "Symlink targets are not traversed for size estimation.</div>"
    )
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def write_findings_html(
    path: str | Path, inventory: dict[str, Any], artifact_inventory: dict[str, Any]
) -> None:
    """Write findings.html."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_findings_html(inventory, artifact_inventory), encoding="utf-8")
