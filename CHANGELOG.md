# Changelog

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
