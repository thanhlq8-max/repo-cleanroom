# Changelog

## v0.8.0

- Version alignment (explicit maintainer release task, 2026-07-05): `pyproject.toml` version bumped from `0.1.0` to `0.8.0`, aligning the package track with the milestone track per `docs/RELEASE_POLICY.md`.
- Aligned stale wording with actual capabilities: README intro/capabilities/roadmap/status, SECURITY.md supported status, CLI parser description, scan `public_safety_check` note, and the `findings.md` safety note no longer describe the tool as v0.1.0/read-only-only.
- Post-merge step: tag `v0.8.0` on the merge commit (tag name equals package version per release policy).
- No package published; TestPyPI/PyPI remain separate explicitly-commanded steps (v0.8.1/v0.8.2).

## v0.7.2

- Added `scripts/benchmark_scan.py` and `repo_cleanroom.demo.benchmark`: reproducible scan/plan benchmark against synthetic workspaces; requires a fresh working directory and writes only inside it.
- Added `docs/PERFORMANCE.md` with measured results (100 repos: scan 0.74 s / plan 0.47 s; 500 repos: scan 3.62 s / plan 2.37 s on Windows 10, Python 3.13) and explicit limitations — no claim beyond the included data.
- Benchmark smoke tests (end-to-end at small scale; reused working directory refused).

## v0.7.1

- Added the `demo-workspace` command: generates a synthetic workspace (web/python/rust repo shapes with node_modules, .venv, __pycache__, dist, target, logs, and a placeholder .env) for trying the scan → plan pipeline safely.
- Refuses to write into an existing non-empty directory, so it can never touch real data (tested).
- `--repo-count` scales the workspace by repeating the python repo shape; used by the v0.7.2 benchmark.
- All content synthetic; the .env value is an obvious placeholder.
- End-to-end test: generated workspace scans and plans successfully, including a BLOCKED finding.

## v0.7.0

- Added the `html-report` command: renders a static, self-contained `findings.html` review page from existing `inventory.json` + `artifact_inventory.json`.
- Single file, inline CSS, no JavaScript, no external resources; risk-badged groups mirror `findings.md` (SAFE → REVIEW → DANGEROUS → BLOCKED, size-sorted).
- Every value from the scanned workspace is HTML-escaped — untrusted repo/file names cannot inject markup (tested with script/img payloads).
- Writes only `findings.html` into `--out-dir`; no other filesystem side effect (tested by snapshot).

## v0.6.1

- Added the `docker-plan` command: builds an informational `docker_cleanup_plan.json` from a docker inventory.
- Fixed policy: stopped workspace-linked containers and dangling images → REVIEW_REQUIRED (manual review suggestions only); everything else → NO_ACTION; every volume → FORBIDDEN_DEFAULT.
- Volumes are never proposed for deletion; the summary pins `volumes_proposed_for_deletion: 0`.
- The plan is not executable: the tool has no Docker mutation capability, recorded as `tool_can_execute_this_plan: false`.
- Pure file transformation with SHA-256 provenance of the source inventory; no Docker invocation.

## v0.6.0

- Added the `docker-scan` command: read-only Docker inventory (`docker_inventory.json`) of containers, images, and volumes, relating compose-labeled objects to the selected workspace root.
- Docker is queried exclusively through a fixed whitelist of read-only `docker` CLI argument lists (`version`, `ps --all`, `images`, `volume ls`, all JSON-formatted), `shell=False`, no user input in argv; a test asserts the whitelist contains no mutating verb.
- No Docker object is created, started, stopped, or removed; the inventory records `docker_mutation_performed: false` and the exact queries used.
- Docker unavailable → clean error, exit 2, no partial file.
- Tests use an injected fake runner, so CI needs no Docker daemon.

## v0.5.1

- Added the `evidence` command: maps an explicitly supplied plain-text evidence file to detected artifacts; writes `command_evidence.json` and `evidence_map.md`.
- Evidence enters only via required `--evidence-file`; there is no code path that locates or reads shell history, and no evidence line is ever executed.
- Every persisted line passes the sanitizer (credential URLs, sensitive flags/assignments, token-shaped strings, protected filenames) per `docs/COMMAND_EVIDENCE_PRIVACY.md`; tests assert raw secrets never reach the outputs.
- Keyword classification maps commands (npm/pip/venv/pytest/cargo/build tools) to the artifact types they plausibly produced; evidence never changes risk classification.
- Mapping is informational only and touches no workspace file (tested by snapshot).

## v0.5.0

- Added `docs/COMMAND_EVIDENCE_PRIVACY.md`: privacy contract for command evidence — no default shell-history access ever, explicit `--evidence-file` input only, no execution of evidence lines, mandatory sanitization (credential URLs, sensitive flag values, token-shaped strings, protected filenames) before anything is persisted, local-only outputs.
- Documentation only; no evidence code exists yet (v0.5.1).

## v0.4.1

- Added the `attest` command: assembles `attestation.json` and `final_report.md` from a plan, its clean action log, and its verify results.
- The report separates entries into cleaned, skipped, failed, blocked, and unchanged, with per-category tables and reasons.
- Attestation status: `ATTESTED`, `ATTESTED_DRY_RUN`, or `NOT_ATTESTED_VERIFICATION_FAILED` (exit 1) — a failed verification is attested as a discrepancy, never as a clean state.
- SHA-256 provenance of all three inputs recorded; mismatched plan/log/verify ids are rejected with no attestation.
- The report explicitly limits its claims to the plan's entries and repeats the no-rollback policy.


## v0.4.0

- Added the `verify` command: read-only comparison of the filesystem against an executed plan and its `clean_action_log.json`; writes `verify.json`.
- Expected-state rules: REMOVED entries must be absent (`FAIL_STILL_PRESENT` otherwise); every non-removed entry must still exist (`FAIL_MISSING` otherwise — detects out-of-band data loss); SKIPPED_CHANGED entries are indeterminate.
- Records SHA-256 provenance of the input plan and action log inside `verify.json`.
- Rejects mismatched plan/log ids or roots with no verdict; exit codes: 0 verified, 1 verification failed, 2 inconsistent inputs.
- Verification modifies nothing (tested by snapshot).

## v0.3.1

- Added `clean_report.md` output for every clean run: status (COMPLETE/PARTIAL/DRY_RUN), per-entry table of everything not removed with reasons, and an explicit no-rollback recovery policy.
- Added `partial` and `proposed_total` to the action-log summary; console prints `PARTIAL: YES/NO` and `ROLLBACK: NOT_AVAILABLE_BY_DESIGN`; `STATUS: CLEAN_PARTIAL` when some proposed entries were not removed.
- Added dry-run parity test: the dry-run would-remove set must equal the real-run removed set on an unchanged workspace.
- Added failure-recovery tests: locked-file removal error → fail-fast, later entries NOT_PROCESSED, partial report; planted-secret skip → PARTIAL status.
- No rollback is claimed anywhere; a partially executed plan requires rescan → replan → reapprove.

## v0.3.0

- Added the `approve` command: issues `approval_token.json` bound to one exact plan via the canonical SHA-256 plan hash (docs/APPROVAL_TOKEN.md); 24-hour expiry; `--approved-by` required.
- Added the `clean` command: removes ONLY SAFE `PROPOSE_REMOVE` entries of one approved plan; requires `--root`, `--plan`, `--token`, `--out-dir`, and `--yes-exact-plan <full plan hash>` — no blanket confirmation.
- Every guard re-checked at delete time: root path guard, symlink identity, secret guard on the entry and on names planted inside it, `.git` refusal, filesystem-boundary refusal; symlinks are removed as links only, targets never touched.
- `--dry-run` reports the exact would-remove set and removes nothing.
- Outputs `clean_action_log.json` (one record per plan entry, every run) and `removed_manifest.json` (real runs only); fail-fast on first error with remaining entries marked NOT_PROCESSED.
- Tampered plan, expired token, mismatched root, or wrong confirmation hash → refusal with zero removals (tested).
- Repaired changelog entries duplicated by manual merge resolution; restored the README/USAGE plan sections lost in the same merges.

## v0.2.2

- Added JSON contract tests pinning the `cleanup_plan.json` schema (top-level, entry, summary, provenance field sets and count/byte consistency).
- Added `cleanup_plan.md` rendering tests: fixed action-group order, size sorting, empty-group omission, and explicit nothing-was-deleted wording.
- Added `examples/sample-plan/cleanup_plan.md`, generated from the committed synthetic sample plan with the real renderer.
- Tests only plus sample evidence; no behavior change; still no removal capability.

## v0.2.1

- Added the `plan` command: builds `cleanup_plan.json` and `cleanup_plan.md` from an existing `artifact_inventory.json`, per `docs/CLEANUP_PLAN_SCHEMA.md`.
- Plan generation is PLAN_ONLY: it proposes, it never removes; tests assert the scanned workspace is byte-identical before and after planning.
- Fixed risk-to-action mapping: SAFE→PROPOSE_REMOVE, REVIEW→REVIEW_REQUIRED, DANGEROUS→NO_ACTION, BLOCKED→FORBIDDEN; SAFE symlinks are never proposed.
- Plan aborts with no partial output if any inventory entry fails the root path guard or has an unknown risk class.
- `--scan-artifacts` and `--out-dir` are required; no hidden defaults.

## v0.1.7

- Grouped the `findings.md` artifact findings section by risk class (`SAFE` → `REVIEW` → `DANGEROUS` → `BLOCKED`) with per-group count and size subtotal.
- Sorted findings inside each risk group by size, largest first.
- Added tests for group ordering, subtotals, and omission of empty groups.
- Report rendering change only; no scan/filesystem side effect change.

## v0.1.6

- Added `docs/RELEASE_POLICY.md`: milestone-vs-package version tracks, alignment rule, release gates, and pre-release checklist.
- Recorded that `pyproject.toml` stays at `0.1.0` until an explicit release task.
- Documentation only; no scanner behavior change.
- No package published.

## v0.1.5

- Added `docs/WINDOWS_QUICKSTART.md` with a sanitized Windows install-and-scan transcript.
- Linked the quickstart from README and `docs/USAGE.md`.
- Documentation only; no scanner behavior change.
- No cleanup/delete command added.

## v0.1.4

- Expanded path guard coverage for Windows-focused temporary-directory scenarios.
- Added sibling-directory and similar-prefix path tests.
- Added root/self and resolved-child path tests.
- Added POSIX-style relative path output test.
- Added symlink-to-sibling coverage with platform skip.
- Kept scan behavior unchanged.

## v0.1.3

- Added a largest-artifacts section to `findings.md`.
- Added tests for largest-artifact ordering.
- Added JSON report schema contract tests.
- Kept scan behavior unchanged.
- Kept v0.1.x read-only scope unchanged.

## v0.1.2

- Added synthetic sample scan evidence under `examples/sample-scan/`.
- Added `docs/SAMPLE_SCAN_EVIDENCE.md`.
- Updated README with sample scan links.
- Updated roadmap with the v0.1.2 evidence/backlog scope.
- No scanner behavior change.
- No cleanup/delete command added.

## v0.1.1

- Added GitHub Actions CI for Python 3.11, 3.12, and 3.13 on Windows.
- Added bug report, feature request, and safety review issue templates.
- Added pull request template with safety checklist.
- Fixed package metadata URLs.
- Added `docs/ROADMAP.md`.

## v0.1.0

- Initial read-only scanner.
- Added Git repo discovery.
- Added manifest detection.
- Added repo-local artifact detection.
- Added path guard, symlink guard, secret guard.
- Added risk classification.
- Added JSON and Markdown reports.
- Added tests and Windows bootstrap scripts.
