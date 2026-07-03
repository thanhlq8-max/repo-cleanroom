# Repo Cleanroom

[![CI](https://github.com/thanhlq8-max/repo-cleanroom/actions/workflows/ci.yml/badge.svg)](https://github.com/thanhlq8-max/repo-cleanroom/actions/workflows/ci.yml)

Repo Cleanroom is a safety-first CLI for developers who clone and run many open-source repositories locally.

It scans a user-selected workspace, discovers Git repositories, detects common repo-local generated artifacts, classifies cleanup risk, and writes JSON/Markdown reports.

> v0.1.0 is **read-only**. It does not delete files, uninstall packages, prune Docker, modify Git state, read shell history, or change system configuration.

## Why this exists

Modern OSS and AI-coding workflows make it easy to clone, install, test, and abandon many repositories. Each repo can leave behind dependency folders, virtual environments, build outputs, caches, coverage files, logs, and runtime artifacts. Over time, a developer workstation becomes difficult to audit and clean safely.

Repo Cleanroom starts with the safe part first:

```text
SCAN -> REPORT -> REVIEW
```

Later versions will add:

```text
SCAN -> EVIDENCE MAP -> USER-APPROVED PLAN -> CLEAN -> VERIFY -> ATTESTATION REPORT
```

## v0.1.0 capabilities

- Discover Git repositories under a selected root.
- Detect project manifests and infer ecosystems.
- Detect common repo-local artifacts such as `node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `dist`, `build`, `target`, `bin`, `obj`, `.next`, and `.nuxt`.
- Classify artifacts into `SAFE`, `REVIEW`, `DANGEROUS`, or `BLOCKED`.
- Block sensitive path patterns such as `.env`, private keys, credentials, wallet-like files, and token-like files.
- Estimate artifact size without following symlinks.
- Generate report artifacts.

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

v0.1.0 has no cleanup/delete command. Detection does not mean removal approval.

Risk classes:

| Risk | Meaning |
|---|---|
| `SAFE` | Common generated artifact that can be proposed for deletion in a future plan engine. Not deleted in v0.1.0. |
| `REVIEW` | May contain user data or runtime output. User review required. |
| `DANGEROUS` | Could affect external/system state or valuable runtime data. Not cleaned in MVP. |
| `BLOCKED` | Sensitive/protected item. Must not be auto-deleted or printed as content. |

## GitHub workflow

Every pull request should keep the safety contract intact:

- scan/report changes must remain read-only;
- cleanup behavior must go through a plan and approval model first;
- destructive behavior requires a dedicated safety review issue;
- CI must pass on Python 3.11, 3.12, and 3.13.

## Roadmap

- `v0.1.0`: safe scanner + JSON/Markdown reports.
- `v0.1.1`: GitHub CI, issue templates, package metadata cleanup.
- `v0.1.2`: sample scan evidence + initial public backlog.
- `v0.2.0`: cleanup plan engine, still no deletion.
- `v0.3.0`: repo-local SAFE clean only, approval-gated.
- `v0.4.0`: post-clean verification and attestation.
- `v0.5.0`: explicit opt-in command evidence mapping.
- `v0.6.0`: Docker scan/plan, no volume deletion.
- `v1.0.0`: stable CLI, schema, safety docs, validation evidence.

## Status

Early alpha. Read-only scanner. No production cleanup claim.
