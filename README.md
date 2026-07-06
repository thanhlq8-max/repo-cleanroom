# Repo Cleanroom

[![CI](https://github.com/thanhlq8-max/repo-cleanroom/actions/workflows/ci.yml/badge.svg)](https://github.com/thanhlq8-max/repo-cleanroom/actions/workflows/ci.yml)

Repo Cleanroom is a safety-first CLI for developers who clone and run many open-source repositories locally.

It scans a user-selected workspace, discovers Git repositories, detects common repo-local generated artifacts, classifies cleanup risk, and writes JSON/Markdown reports.

> `scan`, `plan`, `verify`, `attest`, `evidence`, `docker-scan`, and `docker-plan` are **read-only or report-only**. The only command that removes anything is `clean`, and it acts solely on `SAFE` entries of one byte-exact, human-approved plan with every guard re-checked at delete time. The tool never uninstalls packages, prunes Docker, modifies Git state, reads shell history, or changes system configuration.

## Why this exists

Modern OSS and AI-coding workflows make it easy to clone, install, test, and abandon many repositories. Each repo can leave behind dependency folders, virtual environments, build outputs, caches, coverage files, logs, and runtime artifacts. Over time, a developer workstation becomes difficult to audit and clean safely.

Repo Cleanroom implements the full safety-gated workflow:

```text
SCAN -> PLAN -> APPROVE -> CLEAN -> VERIFY -> ATTESTATION REPORT
```

## Capabilities (v1.0.0)

- `scan` — discover Git repositories, detect manifests and common repo-local artifacts (`node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `dist`, `build`, `target`, and more), classify risk (`SAFE`/`REVIEW`/`DANGEROUS`/`BLOCKED`), estimate sizes without following symlinks, and write JSON/Markdown reports. Read-only.
- `plan` — turn a scan into a reviewable `cleanup_plan.json`/`.md` proposal. Removes nothing.
- `approve` — bind a human approval to one exact plan via its canonical SHA-256 hash (24-hour expiry).
- `clean` — remove ONLY the `SAFE` entries of one approved plan; exact-hash confirmation required; every guard (root boundary, symlink, secret, `.git`) re-checked at delete time; `--dry-run` supported; no rollback is claimed.
- `verify` / `attest` — read-only post-clean verification and a final evidence pack separating cleaned / skipped / failed / blocked / unchanged.
- `evidence` — opt-in mapping of a user-supplied command list to artifacts; never reads shell history; sanitized output only.
- `docker-scan` / `docker-plan` — read-only Docker inventory via a fixed CLI whitelist and an informational plan; volumes are never proposed for deletion; no Docker mutation capability exists.
- `html-report` — self-contained static review page (no scripts, fully escaped).
- `demo-workspace` — synthetic try-it fixture generator (refuses non-empty targets).

## Non-goals

Repo Cleanroom is not:

- a one-click PC optimizer;
- a malware scanner;
- an antivirus tool;
- a registry cleaner;
- a privacy shredder;
- a Docker volume remover;
- a global package uninstaller.

## Install locally

```powershell
git clone https://github.com/thanhlq8-max/repo-cleanroom.git
cd repo-cleanroom
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .[dev]
```

## Run a scan

`--root` and `--out-dir` are required. There is no hidden output-directory default.

```powershell
repo-cleanroom scan --root F:\GitHub --out-dir .cleanroom
```

Outputs:

```text
.cleanroom\schema_version.json
.cleanroom\inventory.json
.cleanroom\artifact_inventory.json
.cleanroom\findings.md
.cleanroom\public_safety_check.json
```

A sanitized Windows terminal transcript of a full install-and-scan session is available in [`docs/WINDOWS_QUICKSTART.md`](docs/WINDOWS_QUICKSTART.md).

## Build a cleanup plan (removes nothing)

The `plan` command turns a scan's `artifact_inventory.json` into a reviewable proposal. It is PLAN_ONLY: it writes `cleanup_plan.json` and `cleanup_plan.md` and removes nothing. A plan is not permission.

```powershell
repo-cleanroom plan --scan-artifacts .cleanroom\artifact_inventory.json --out-dir .cleanroom
```

Schema: [`docs/CLEANUP_PLAN_SCHEMA.md`](docs/CLEANUP_PLAN_SCHEMA.md). Sample output: [`examples/sample-plan/`](examples/sample-plan/).

## Approve and clean (v0.3.x, approval-gated)

Removal exists only behind an exact-plan approval token ([`docs/APPROVAL_TOKEN.md`](docs/APPROVAL_TOKEN.md)) and the safety model in [`docs/CLEANER_SAFETY_MODEL.md`](docs/CLEANER_SAFETY_MODEL.md). Review `cleanup_plan.md`, then:

```powershell
repo-cleanroom approve --plan .cleanroom\cleanup_plan.json --approved-by "your-name" --out-dir .cleanroom
repo-cleanroom clean --root F:\GitHub --plan .cleanroom\cleanup_plan.json --token .cleanroom\approval_token.json --yes-exact-plan <PLAN_HASH> --dry-run --out-dir .cleanroom
repo-cleanroom clean --root F:\GitHub --plan .cleanroom\cleanup_plan.json --token .cleanroom\approval_token.json --yes-exact-plan <PLAN_HASH> --out-dir .cleanroom
```

- Only `SAFE` entries proposed by the exact approved plan are removed; `REVIEW`, `DANGEROUS`, and `BLOCKED` items are never touched.
- Any change to the plan invalidates the approval. Tokens expire after 24 hours.
- Every guard (root boundary, symlink/junction, secret, `.git`) is re-checked at delete time.
- There is no rollback. Always run `--dry-run` first.

## Sample scan evidence

Synthetic sample output is available in [`examples/sample-scan/`](examples/sample-scan/).

Start with:

- [`docs/SAMPLE_SCAN_EVIDENCE.md`](docs/SAMPLE_SCAN_EVIDENCE.md)
- [`examples/sample-scan/findings.md`](examples/sample-scan/findings.md)
- [`examples/sample-scan/artifact_inventory.json`](examples/sample-scan/artifact_inventory.json)

The sample demonstrates `SAFE`, `REVIEW`, and `BLOCKED` findings without deleting anything.

For a sanitized Windows quickstart transcript, see
[`docs/WINDOWS_QUICKSTART_TRANSCRIPT.md`](docs/WINDOWS_QUICKSTART_TRANSCRIPT.md).

## Validate locally

```powershell
py -m compileall src tests
py -m pytest -q
py -m build
```

## Safety model

Repo Cleanroom treats target repository files as untrusted data. It does not execute scripts from scanned repositories.

Detection does not mean removal approval. `scan` and `plan` never modify the workspace. Removal exists only in the approval-gated `clean` command (v0.3.x), which acts solely on SAFE entries of one byte-exact approved plan and re-checks every guard at delete time.

Risk classes:

| Risk | Meaning |
|---|---|
| `SAFE` | Common generated artifact eligible for a `PROPOSE_REMOVE` plan entry. Removed only under an approved plan. |
| `REVIEW` | May contain user data or runtime output. User review required. |
| `DANGEROUS` | Could affect external/system state or valuable runtime data. Never cleaned. |
| `BLOCKED` | Sensitive/protected item. Must not be auto-deleted or printed as content. |

## GitHub workflow

Every pull request should keep the safety contract intact:

- scan/report changes must remain read-only;
- cleanup behavior must go through a plan and approval model first;
- destructive behavior requires a dedicated safety review issue;
- CI must pass on Python 3.11, 3.12, and 3.13.

## Roadmap

- `v0.1.x` — safe scanner, reports, CI, sample evidence, path-guard hardening. DONE.
- `v0.2.x` — cleanup plan engine (schema, approval-token design, PLAN_ONLY plan command). DONE.
- `v0.3.x` — approval-gated SAFE clean with dry-run and recovery reporting. DONE.
- `v0.4.x` — post-clean verification and attestation. DONE.
- `v0.5.x` — explicit opt-in command evidence mapping. DONE.
- `v0.6.x` — Docker read-only scan and informational plan, no volume deletion. DONE.
- `v0.7.x` — HTML report, demo workspace, reproducible benchmark. DONE.
- `v0.8.x` — version alignment and pre-release packaging readiness. DONE.
- `v0.9.x` — public beta stabilization and safety audit. DONE.
- `v1.0.0` — stable CLI, frozen schemas, safety docs, validation evidence. DONE.

## Status

Stable (v1.0.0). The full SCAN → PLAN → APPROVE → CLEAN → VERIFY → ATTEST pipeline is implemented and CI-tested on Python 3.11/3.12/3.13. Output schemas are frozen per [`docs/SCHEMA_STABILITY.md`](docs/SCHEMA_STABILITY.md). Removal remains approval-gated with no rollback claim. Not yet published to PyPI.
