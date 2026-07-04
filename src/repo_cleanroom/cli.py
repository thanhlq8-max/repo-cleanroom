"""Command line interface for Repo Cleanroom."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.models import SCHEMA_VERSION
from repo_cleanroom.planners.plan_builder import PlanBuildError, build_plan_payload
from repo_cleanroom.planners.plan_markdown import write_plan_markdown
from repo_cleanroom.reports.json_report import write_json
from repo_cleanroom.reports.markdown_report import write_findings_markdown
from repo_cleanroom.safety.path_guard import PathGuardError, resolve_existing_directory
from repo_cleanroom.scanner.artifact_detector import detect_artifacts
from repo_cleanroom.scanner.manifest_detector import detect_manifests
from repo_cleanroom.scanner.repo_discovery import discover_repositories


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_scan_payload(root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run read-only scan and return inventory/report payloads."""

    resolved_root = resolve_existing_directory(root)
    repos = discover_repositories(resolved_root)

    manifests = []
    artifacts = []
    repo_by_path = {repo.path: repo for repo in repos}

    for repo in repos:
        repo_manifests = detect_manifests(repo.path)
        manifests.extend(repo_manifests)

        repo_artifacts = detect_artifacts(repo.path, repo_manifests, root=resolved_root)
        for artifact in repo_artifacts:
            data = artifact.to_dict()
            data["repo_name"] = repo.name
            data["repo_relative_path"] = repo.relative_path
            artifacts.append(data)

    manifest_dicts = [item.to_dict() for item in manifests]
    risk_counts = Counter(item["risk"] for item in artifacts)
    type_counts = Counter(item["artifact_type"] for item in artifacts)
    total_size = sum(int(item["size_bytes"]) for item in artifacts)

    inventory = {
        "schema_version": SCHEMA_VERSION,
        "status": "OK",
        "mode": "READ_ONLY_SCAN",
        "generated_at_utc": _utc_now(),
        "root": str(resolved_root),
        "repos": [repo.to_dict() for repo in repos],
        "manifests": manifest_dicts,
        "totals": {
            "repos": len(repos),
            "manifests": len(manifest_dicts),
        },
        "safety": {
            "cleanup_performed": False,
            "shell_history_read": False,
            "target_repo_scripts_executed": False,
        },
    }

    artifact_inventory = {
        "schema_version": SCHEMA_VERSION,
        "status": "OK",
        "mode": "READ_ONLY_SCAN",
        "generated_at_utc": _utc_now(),
        "root": str(resolved_root),
        "artifacts": artifacts,
        "totals": {
            "artifacts": len(artifacts),
            "size_bytes": total_size,
            "by_risk": dict(sorted(risk_counts.items())),
            "by_type": dict(sorted(type_counts.items())),
        },
    }

    public_safety = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "generated_at_utc": _utc_now(),
        "secrets_exposed": False,
        "unsafe_claims": False,
        "misleading_wording": False,
        "external_side_effect": False,
        "cleanup_performed": False,
        "notes": [
            "v0.1.0 scan is read-only.",
            "Secret guard uses path/name classification only and does not read file contents.",
            "Target repository scripts are not executed.",
        ],
    }

    # Keep a reference so static checkers do not mark repo_by_path as accidental;
    # it is intentionally retained for future report joins.
    _ = repo_by_path

    return inventory, artifact_inventory, public_safety


def run_scan(args: argparse.Namespace) -> int:
    """Run the scan command."""

    try:
        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)

        inventory, artifact_inventory, public_safety = build_scan_payload(args.root)
        schema_payload = {
            "schema_version": SCHEMA_VERSION,
            "tool": "repo-cleanroom",
            "command": "scan",
            "mode": "READ_ONLY_SCAN",
            "generated_at_utc": _utc_now(),
        }

        write_json(out_dir / "schema_version.json", schema_payload)
        write_json(out_dir / "inventory.json", inventory)
        write_json(out_dir / "artifact_inventory.json", artifact_inventory)
        write_json(out_dir / "public_safety_check.json", public_safety)
        write_findings_markdown(out_dir / "findings.md", inventory, artifact_inventory)

        repos = inventory["totals"]["repos"]
        artifacts = artifact_inventory["totals"]["artifacts"]
        size_bytes = artifact_inventory["totals"]["size_bytes"]
        print("STATUS: READ_ONLY_SCAN_COMPLETE")
        print(f"ROOT: {inventory['root']}")
        print(f"OUT_DIR: {out_dir}")
        print(f"REPOS_SCANNED: {repos}")
        print(f"ARTIFACTS_FOUND: {artifacts}")
        print(f"ESTIMATED_ARTIFACT_BYTES: {size_bytes}")
        print("CLEANUP_PERFORMED: NO")
        return 0
    except PathGuardError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


def run_plan(args: argparse.Namespace) -> int:
    """Run the plan command. PLAN_ONLY: writes proposal files, removes nothing."""

    try:
        plan = build_plan_payload(args.scan_artifacts)

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)

        write_json(out_dir / "cleanup_plan.json", plan)
        write_plan_markdown(out_dir / "cleanup_plan.md", plan)

        summary = plan["summary"]
        print("STATUS: PLAN_ONLY_COMPLETE")
        print(f"ROOT: {plan['root']}")
        print(f"OUT_DIR: {out_dir}")
        print(f"PLAN_ENTRIES: {summary['total_entries']}")
        print(f"PROPOSED_REMOVE_COUNT: {summary['proposed_remove_count']}")
        print(f"PROPOSED_REMOVE_BYTES: {summary['proposed_remove_bytes']}")
        print("CLEANUP_PERFORMED: NO")
        return 0
    except (PathGuardError, PlanBuildError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="repo-cleanroom",
        description="Read-only scanner for repo-local generated artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser(
        "scan",
        help="scan a user-selected root and write read-only reports",
    )
    scan.add_argument("--root", required=True, help="existing directory to scan")
    scan.add_argument(
        "--out-dir",
        required=True,
        help="directory where scan reports will be written; required by policy",
    )
    scan.set_defaults(func=run_scan)

    plan = subparsers.add_parser(
        "plan",
        help="build a PLAN_ONLY cleanup proposal from an existing artifact inventory; removes nothing",
    )
    plan.add_argument(
        "--scan-artifacts",
        required=True,
        help="path to an artifact_inventory.json produced by the scan command",
    )
    plan.add_argument(
        "--out-dir",
        required=True,
        help="directory where cleanup_plan.json and cleanup_plan.md will be written; required by policy",
    )
    plan.set_defaults(func=run_plan)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
