"""Map explicitly supplied command evidence to detected artifacts.

Evidence lines are data: they are classified by simple keyword rules, sanitized,
and matched against artifact types from an existing artifact inventory. Nothing
is executed and no filesystem path outside the two input files is read.
Evidence never changes risk classification.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.evidence.sanitizer import sanitize_line

EVIDENCE_SCHEMA_VERSION = "0.5.0"

# Keyword rules: first match wins. Maps a command-line pattern to the artifact
# types it plausibly produced and a short tool label.
_CLASSIFICATION_RULES: list[tuple[tuple[str, ...], str, list[str]]] = [
    (("npm install", "npm ci", "yarn install", "yarn add", "pnpm install"), "node package install", ["node_dependencies"]),
    (("npm run build", "yarn build", "pnpm build", "vite build", "next build", "nuxt build"), "node build", ["build_output"]),
    (("python -m venv", "py -m venv", "virtualenv", "poetry install", "pipenv install"), "python environment setup", ["python_virtualenv"]),
    (("pip install", "py -m pip install", "python -m pip install"), "python package install", ["python_virtualenv"]),
    (("pytest", "py -m pytest", "python -m pytest"), "python test run", ["python_cache"]),
    (("cargo build", "cargo test", "cargo run"), "rust build/test", ["rust_build_output"]),
    (("dotnet build", "dotnet test", "msbuild"), "dotnet build", ["build_output"]),
    (("make", "cmake", "gradle", "gradlew", "mvn "), "generic build", ["build_output"]),
    (("py -m build", "python -m build"), "python package build", ["build_output"]),
]


class EvidenceError(ValueError):
    """Raised when evidence inputs cannot produce a mapping."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _classify(line: str) -> tuple[str | None, list[str]]:
    lowered = line.lower()
    for needles, tool, artifact_types in _CLASSIFICATION_RULES:
        if any(needle in lowered for needle in needles):
            return tool, list(artifact_types)
    return None, []


def _load_artifact_inventory(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"artifact inventory is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or "artifacts" not in payload:
        raise EvidenceError("artifact inventory missing required field: artifacts")
    return payload


def build_evidence_payload(evidence_file: str | Path, scan_artifacts: str | Path) -> dict[str, Any]:
    """Build the command_evidence.json payload. Reads only the two named files."""

    evidence_path = Path(evidence_file).expanduser()
    if not evidence_path.is_file():
        raise EvidenceError(f"evidence file not found: {evidence_path}")
    inventory_path = Path(scan_artifacts).expanduser()
    if not inventory_path.is_file():
        raise EvidenceError(f"artifact inventory not found: {inventory_path}")

    inventory = _load_artifact_inventory(inventory_path)
    raw_text = evidence_path.read_text(encoding="utf-8", errors="replace")

    lines: list[dict[str, Any]] = []
    for index, raw_line in enumerate(raw_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tool, artifact_types = _classify(stripped)
        lines.append(
            {
                "index": index,
                "sanitized": sanitize_line(stripped),
                "tool": tool,
                "supports_artifact_types": artifact_types,
            }
        )

    supported_types = {t for item in lines for t in item["supports_artifact_types"]}
    artifacts = []
    for record in inventory.get("artifacts", []):
        artifact_type = record.get("artifact_type")
        supporting = [
            item["index"] for item in lines if artifact_type in item["supports_artifact_types"]
        ]
        artifacts.append(
            {
                "repo_relative_path": record.get("repo_relative_path"),
                "relative_path": record.get("relative_path"),
                "artifact_type": artifact_type,
                "risk": record.get("risk"),
                "supporting_line_indexes": supporting,
            }
        )

    return {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "mode": "EVIDENCE_MAPPING_ONLY",
        "source_evidence_file": str(evidence_path),
        "source_artifact_inventory": str(inventory_path),
        "lines": lines,
        "artifacts": artifacts,
        "summary": {
            "evidence_lines": len(lines),
            "classified_lines": sum(1 for item in lines if item["tool"] is not None),
            "unclassified_lines": sum(1 for item in lines if item["tool"] is None),
            "artifact_types_with_evidence": sorted(supported_types),
            "artifacts_with_evidence": sum(1 for a in artifacts if a["supporting_line_indexes"]),
        },
    }


def render_evidence_map(payload: dict[str, Any]) -> str:
    """Render evidence_map.md from a command evidence payload."""

    lines_by_index = {item["index"]: item for item in payload.get("lines", [])}
    out: list[str] = []
    out.append("# Command Evidence Map")
    out.append("")
    out.append("STATUS: EVIDENCE_MAPPING_ONLY — informational; changes no risk classification.")
    out.append("")
    out.append("## Summary")
    out.append("")
    summary = payload.get("summary", {})
    out.append(f"- Evidence lines considered: {summary.get('evidence_lines', 0)}")
    out.append(f"- Classified: {summary.get('classified_lines', 0)}")
    out.append(f"- Unclassified: {summary.get('unclassified_lines', 0)}")
    out.append(f"- Artifacts with supporting evidence: {summary.get('artifacts_with_evidence', 0)}")
    out.append("")
    out.append("## Artifacts and supporting evidence")
    out.append("")
    out.append("| Artifact | Type | Risk | Supporting evidence (sanitized) |")
    out.append("|---|---|---|---|")
    for artifact in payload.get("artifacts", []):
        supporting = [
            f"`{lines_by_index[i]['sanitized']}`"
            for i in artifact.get("supporting_line_indexes", [])
            if i in lines_by_index
        ]
        display = f"{artifact.get('repo_relative_path')}/{artifact.get('relative_path')}"
        out.append(
            f"| `{display}` | `{artifact.get('artifact_type')}` | {artifact.get('risk')} | "
            f"{'<br>'.join(supporting) if supporting else '(none)'} |"
        )
    out.append("")

    unclassified = [item for item in payload.get("lines", []) if item.get("tool") is None]
    if unclassified:
        out.append("## Unclassified evidence lines")
        out.append("")
        for item in unclassified:
            out.append(f"- line {item['index']}: `{item['sanitized']}`")
        out.append("")

    out.append("## Privacy notes")
    out.append("")
    out.append("- All lines above were sanitized per docs/COMMAND_EVIDENCE_PRIVACY.md before writing.")
    out.append("- Evidence was supplied explicitly by the user; no shell history was read.")
    out.append("- No evidence line was executed.")
    out.append("")
    return "\n".join(out) + "\n"
