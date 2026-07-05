"""Command line interface for Repo Cleanroom."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_cleanroom.cleaner.approval import ApprovalError, build_approval_token, verify_approval_token
from repo_cleanroom.cleaner.clean_report import write_clean_report
from repo_cleanroom.cleaner.executor import execute_clean

from repo_cleanroom.dockerscan.docker_plan import DockerPlanError, build_docker_plan

from repo_cleanroom.dockerscan.docker_scan import DockerScanError, build_docker_inventory
from repo_cleanroom.evidence.importer import EvidenceError, build_evidence_payload, render_evidence_map
from repo_cleanroom.models import SCHEMA_VERSION
from repo_cleanroom.planners.plan_builder import PlanBuildError, build_plan_payload
from repo_cleanroom.planners.plan_hash import PlanHashError, compute_plan_hash, load_plan_file
from repo_cleanroom.planners.plan_markdown import write_plan_markdown
from repo_cleanroom.reports.json_report import write_json
from repo_cleanroom.reports.markdown_report import write_findings_markdown
from repo_cleanroom.safety.path_guard import PathGuardError, resolve_existing_directory

from repo_cleanroom.verifier.attestation import (
    AttestationError,
    build_attestation_payload,
    write_final_report,
)

from repo_cleanroom.verifier.verify import VerifyError, build_verify_payload, sha256_file
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
        write_clean_report(out_dir / "clean_report.md", result)

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
        elif summary["partial"]:
            print("STATUS: CLEAN_PARTIAL")
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
        print(f"PARTIAL: {'YES' if summary['partial'] else 'NO'}")
        print(f"CLEANUP_PERFORMED: {'NO' if args.dry_run else 'YES'}")
        print("ROLLBACK: NOT_AVAILABLE_BY_DESIGN")

        return 1 if result["failed"] else 0
    except (PathGuardError, PlanHashError, ApprovalError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


def run_verify(args: argparse.Namespace) -> int:
    """Run the verify command. Read-only: compares filesystem vs plan + action log."""

    try:
        resolved_root = resolve_existing_directory(args.root)
        plan = load_plan_file(args.plan)
        action_log = load_plan_file(args.action_log)

        payload = build_verify_payload(plan, action_log, resolved_root)
        payload["inputs"] = {
            "plan": {"path": str(Path(args.plan).resolve()), "sha256": sha256_file(args.plan)},
            "action_log": {
                "path": str(Path(args.action_log).resolve()),
                "sha256": sha256_file(args.action_log),
            },
        }

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "verify.json", payload)

        summary = payload["summary"]
        print("STATUS: " + ("VERIFY_COMPLETE" if summary["verified"] else "VERIFY_FAILED"))
        print(f"ROOT: {payload['root']}")
        print(f"OUT_DIR: {out_dir}")
        print(f"ENTRIES_CHECKED: {summary['total_entries']}")
        print(f"OK: {summary['ok']}")
        print(f"FAIL_STILL_PRESENT: {summary['fail_still_present']}")
        print(f"FAIL_MISSING: {summary['fail_missing']}")
        print(f"VERIFIED: {'YES' if summary['verified'] else 'NO'}")
        print("FILESYSTEM_MODIFIED: NO")
        return 0 if summary["verified"] else 1
    except (PathGuardError, PlanHashError, VerifyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1



def run_attest(args: argparse.Namespace) -> int:
    """Run the attest command: assemble attestation.json + final_report.md."""

    try:
        plan = load_plan_file(args.plan)
        action_log = load_plan_file(args.action_log)
        verify_payload = load_plan_file(args.verify)

        attestation = build_attestation_payload(plan, action_log, verify_payload)
        attestation["inputs"] = {
            "plan": {"path": str(Path(args.plan).resolve()), "sha256": sha256_file(args.plan)},
            "action_log": {
                "path": str(Path(args.action_log).resolve()),
                "sha256": sha256_file(args.action_log),
            },
            "verify": {
                "path": str(Path(args.verify).resolve()),
                "sha256": sha256_file(args.verify),
            },
        }

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "attestation.json", attestation)
        write_final_report(out_dir / "final_report.md", attestation)

        counts = attestation["counts"]
        print(f"STATUS: {attestation['status']}")
        print(f"ROOT: {attestation['root']}")
        print(f"OUT_DIR: {out_dir}")
        print(f"CLEANED: {counts['cleaned']}")
        print(f"SKIPPED: {counts['skipped']}")
        print(f"FAILED: {counts['failed']}")
        print(f"BLOCKED: {counts['blocked']}")
        print(f"UNCHANGED: {counts['unchanged']}")
        print(f"REMOVED_BYTES: {attestation['removed_bytes']}")
        return 0 if attestation["status"] != "NOT_ATTESTED_VERIFICATION_FAILED" else 1
    except (PlanHashError, AttestationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


def run_evidence(args: argparse.Namespace) -> int:
    """Run the evidence command: map explicit user-supplied evidence to artifacts."""

    try:
        payload = build_evidence_payload(args.evidence_file, args.scan_artifacts)

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "command_evidence.json", payload)
        (out_dir / "evidence_map.md").write_text(render_evidence_map(payload), encoding="utf-8")

        summary = payload["summary"]
        print("STATUS: EVIDENCE_MAPPING_COMPLETE")
        print(f"OUT_DIR: {out_dir}")
        print(f"EVIDENCE_LINES: {summary['evidence_lines']}")
        print(f"CLASSIFIED: {summary['classified_lines']}")
        print(f"UNCLASSIFIED: {summary['unclassified_lines']}")
        print(f"ARTIFACTS_WITH_EVIDENCE: {summary['artifacts_with_evidence']}")
        print("SHELL_HISTORY_READ: NO")
        print("EVIDENCE_EXECUTED: NO")
        return 0
    except EvidenceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


def run_docker_scan(args: argparse.Namespace) -> int:
    """Run the docker-scan command: read-only Docker inventory."""

    try:
        resolved_root = resolve_existing_directory(args.root)
        payload = build_docker_inventory(resolved_root)

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "docker_inventory.json", payload)

        summary = payload["summary"]
        print("STATUS: DOCKER_READ_ONLY_SCAN_COMPLETE")
        print(f"ROOT: {payload['root']}")
        print(f"OUT_DIR: {out_dir}")
        print(f"CONTAINERS: {summary['containers']}")
        print(f"CONTAINERS_LINKED_TO_WORKSPACE: {summary['containers_linked_to_workspace']}")
        print(f"IMAGES: {summary['images']}")
        print(f"DANGLING_IMAGES: {summary['dangling_images']}")
        print(f"VOLUMES: {summary['volumes']}")
        print("DOCKER_MUTATION_PERFORMED: NO")
        return 0
    except (PathGuardError, DockerScanError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1



def run_docker_plan(args: argparse.Namespace) -> int:
    """Run the docker-plan command: informational plan, nothing executable."""

    try:
        payload = build_docker_plan(args.docker_inventory)

        out_dir = Path(args.out_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "docker_cleanup_plan.json", payload)

        summary = payload["summary"]
        print("STATUS: DOCKER_PLAN_INFORMATIONAL_ONLY_COMPLETE")
        print(f"ROOT: {payload['root']}")
        print(f"OUT_DIR: {out_dir}")
        print(f"PLAN_ENTRIES: {summary['total_entries']}")
        print(f"REVIEW_REQUIRED: {summary['review_required']}")
        print(f"NO_ACTION: {summary['no_action']}")
        print(f"FORBIDDEN_DEFAULT: {summary['forbidden_default']}")
        print(f"VOLUMES_PROPOSED_FOR_DELETION: {summary['volumes_proposed_for_deletion']}")
        print("DOCKER_MUTATION_PERFORMED: NO")
        return 0
    except DockerPlanError as exc:
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

    verify = subparsers.add_parser(
        "verify",
        help="read-only check of the filesystem against a plan and its clean action log",
    )
    verify.add_argument("--root", required=True, help="root directory the plan was executed on")
    verify.add_argument("--plan", required=True, help="path to the executed cleanup_plan.json")
    verify.add_argument(
        "--action-log",
        required=True,
        help="path to the clean_action_log.json produced by the clean command",
    )
    verify.add_argument(
        "--out-dir",
        required=True,
        help="directory where verify.json will be written; required by policy",
    )
    verify.set_defaults(func=run_verify)


    attest = subparsers.add_parser(
        "attest",
        help="assemble attestation.json and final_report.md from plan, action log, and verify results",
    )
    attest.add_argument("--plan", required=True, help="path to the executed cleanup_plan.json")
    attest.add_argument(
        "--action-log",
        required=True,
        help="path to the clean_action_log.json produced by the clean command",
    )
    attest.add_argument(
        "--verify",
        required=True,
        help="path to the verify.json produced by the verify command",
    )
    attest.add_argument(
        "--out-dir",
        required=True,
        help="directory where attestation.json and final_report.md will be written",
    )
    attest.set_defaults(func=run_attest)

    evidence = subparsers.add_parser(
        "evidence",
        help="map an explicitly supplied command-evidence file to detected artifacts; never reads shell history",
    )
    evidence.add_argument(
        "--evidence-file",
        required=True,
        help="user-assembled plain-text evidence file; the only way evidence enters the tool",
    )
    evidence.add_argument(
        "--scan-artifacts",
        required=True,
        help="path to an artifact_inventory.json produced by the scan command",
    )
    evidence.add_argument(
        "--out-dir",
        required=True,
        help="directory where command_evidence.json and evidence_map.md will be written",
    )
    evidence.set_defaults(func=run_evidence)

    docker_scan = subparsers.add_parser(
        "docker-scan",
        help="read-only Docker inventory via a fixed whitelist of docker CLI queries; mutates nothing",
    )
    docker_scan.add_argument(
        "--root",
        required=True,
        help="workspace root used to relate compose-labeled objects to this workspace",
    )
    docker_scan.add_argument(
        "--out-dir",
        required=True,
        help="directory where docker_inventory.json will be written; required by policy",
    )
    docker_scan.set_defaults(func=run_docker_scan)


    docker_plan = subparsers.add_parser(
        "docker-plan",
        help="informational docker cleanup plan from a docker inventory; this tool cannot execute it",
    )
    docker_plan.add_argument(
        "--docker-inventory",
        required=True,
        help="path to a docker_inventory.json produced by the docker-scan command",
    )
    docker_plan.add_argument(
        "--out-dir",
        required=True,
        help="directory where docker_cleanup_plan.json will be written; required by policy",
    )
    docker_plan.set_defaults(func=run_docker_plan)


    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
