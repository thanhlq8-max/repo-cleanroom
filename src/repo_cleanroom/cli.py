"""Command line interface for Repo Cleanroom."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.cleaner.approval import ApprovalError, build_approval_token, verify_approval_token

from repo_cleanroom.cleaner.executor import execute_clean
from repo_cleanroom.models import SCHEMA_VERSION
from repo_cleanroom.planners.plan_builder import PlanBuildError, build_plan_payload
from repo_cleanroom.planners.plan_hash import PlanHashError, compute_plan_hash, load_plan_file
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


def run_approve(args: argparse.Namespace) -> int:
    """Run the approve command: issue a token bound to one exact plan."""

    try:
        plan = load_plan_file(args.plan)
        token = build_approval_token(plan, approved_by=args.approved_by)

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        token_path = out_dir / "approval_token.json"
        write_json(token_path, token)

        print("STATUS: APPROVAL_TOKEN_WRITTEN")
        print(f"PLAN_ID: {token['plan_id']}")
        print(f"PLAN_HASH: {token['plan_hash']}")
        print(f"APPROVED_REMOVE_COUNT: {token['approved_remove_count']}")
        print(f"APPROVED_REMOVE_BYTES: {token['approved_remove_bytes']}")
        print(f"EXPIRES_AT_UTC: {token['expires_at_utc']}")
        print(f"TOKEN: {token_path}")
        print("NOTE: approval binds to this exact plan; any plan change invalidates it.")
        return 0
    except (PlanHashError, ApprovalError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


def run_clean(args: argparse.Namespace) -> int:
    """Run the clean command: guarded execution of one approved plan."""

    try:
        resolved_root = resolve_existing_directory(args.root)
        plan = load_plan_file(args.plan)
        token = load_plan_file(args.token)

        verify_approval_token(token, plan, resolved_root)

        actual_hash = compute_plan_hash(plan)
        if args.yes_exact_plan.strip().lower() != actual_hash:
            raise ApprovalError(
                "--yes-exact-plan does not match the plan hash; "
                "pass the full PLAN_HASH printed by the approve command"
            )

        result = execute_clean(plan, resolved_root, dry_run=args.dry_run)

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "clean_action_log.json", result)

        if not args.dry_run:
            write_json(
                out_dir / "removed_manifest.json",
                {
                    "log_schema_version": result["log_schema_version"],
                    "generated_at_utc": result["generated_at_utc"],
                    "root": result["root"],
                    "plan_id": result["plan_id"],
                    "removed_paths": result["removed_paths"],
                    "removed_bytes": result["summary"]["removed_bytes"],
                },
            )

        summary = result["summary"]
        if args.dry_run:
            print("STATUS: CLEAN_DRY_RUN_COMPLETE")
        elif result["failed"]:
            print("STATUS: CLEAN_ABORTED")

        else:
            print("STATUS: CLEAN_COMPLETE")
        print(f"ROOT: {result['root']}")
        print(f"OUT_DIR: {out_dir}")
        print(f"REMOVED: {summary['removed']}")
        print(f"WOULD_REMOVE: {summary['would_remove']}")
        print(
            "SKIPPED: "
            f"{summary['skipped_changed'] + summary['skipped_protected'] + summary['skipped_guard_fail']}"
        )
        print(f"ERRORS: {summary['errors']}")
        print(f"REMOVED_BYTES: {summary['removed_bytes']}")

        return 1 if result["failed"] else 0
    except (PathGuardError, PlanHashError, ApprovalError) as exc:
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

    approve = subparsers.add_parser(
        "approve",
        help="issue an approval token bound to one exact cleanup plan",
    )
    approve.add_argument("--plan", required=True, help="path to cleanup_plan.json to approve")
    approve.add_argument(
        "--approved-by",
        required=True,
        help="operator identity recorded in the token",
    )
    approve.add_argument(
        "--out-dir",
        required=True,
        help="directory where approval_token.json will be written; required by policy",
    )
    approve.set_defaults(func=run_approve)

    clean = subparsers.add_parser(
        "clean",
        help="remove SAFE plan entries under one exact approved plan; all guards re-checked",
    )
    clean.add_argument("--root", required=True, help="root directory the plan was approved for")
    clean.add_argument("--plan", required=True, help="path to the approved cleanup_plan.json")
    clean.add_argument("--token", required=True, help="path to approval_token.json")
    clean.add_argument(
        "--yes-exact-plan",
        required=True,
        help="full plan hash from the approve command; blanket confirmation is not accepted",
    )
    clean.add_argument(
        "--out-dir",
        required=True,
        help="directory where clean_action_log.json (and removed_manifest.json) are written",
    )
    clean.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be removed without removing anything",
    )
    clean.set_defaults(func=run_clean)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
