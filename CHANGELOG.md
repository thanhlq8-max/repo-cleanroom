# Changelog

## Unreleased

- No changes yet.

## v1.1.0

Release date: 2026-07-08.

This MINOR release keeps the v1.0.0 safety contract intact while improving scan
coverage, monorepo handling, operator-controlled scan configuration, cross-platform
CI coverage, and publishing readiness. All schema changes are additive only; frozen
schema version fields remain unchanged.

- Optional scan configuration (`scan --config <file.toml>`, `docs/CONFIG.md`):
  - `ignore` — fnmatch globs (matched against the repo-relative POSIX path and the
    basename) exclude paths; ignored directories are pruned.
  - `extra_artifact_names` — additional names to detect; classified by the normal
    risk policy, so unknown names become REVIEW, never auto-SAFE.
  - Config can only narrow the scan (ignore) or flag more as REVIEW (extra names) —
    it can never widen what the tool would propose for removal.
  - The applied config is recorded under a new additive `scan_config` field in
    `inventory.json` / `artifact_inventory.json` for provenance (scan schema
    version unchanged; the field is optional/additive). Never auto-discovered.
- Nested / monorepo artifact detection: `scan` now finds artifacts in subdirectories
  (e.g. `packages/*/node_modules`, `apps/web/.next`, a nested `dist`/`target`), not
  just the repo root. The walk never follows symlinks or junctions, skips VCS
  internals (`.git`/`.hg`/`.svn`), never descends into a detected artifact (so nested
  `node_modules` inside `node_modules` is reported once), and is depth-bounded
  (`DEFAULT_MAX_DEPTH = 8`). `artifact_inventory.json` `relative_path` is now the
  POSIX path from the repo root; top-level artifacts keep their bare name, so existing
  consumers are unaffected. A nested `.env`/secret is still classified BLOCKED
  wherever it lives. Additive; no schema field or enum change.
- Cross-platform CI: the test matrix now runs on Ubuntu and macOS in addition to
  Windows (Ubuntu × 3.11/3.12/3.13, Windows × 3.11/3.12/3.13, macOS × 3.13). This
  actually executes the symlink safety tests, which skip on Windows without symlink
  privilege — the POSIX guard path is now validated in CI, backing the
  `Operating System :: POSIX` classifier. Workflow commands use `python` (the `py`
  launcher is Windows-only).
- Broadened artifact detection (additive, no schema change; new `artifact_type` values
  and manifest ecosystems, risk classes unchanged):
  - New SAFE regenerable dirs: `.output`, `.svelte-kit`, `.astro`, `.turbo`,
    `.parcel-cache`, `.angular` (Node); `__pypackages__`, `.hypothesis`,
    `.ipynb_checkpoints`, `.eggs` (Python); `.gradle` (JVM); `.dart_tool` (Dart).
  - New manifest ecosystems detected: Java/Maven (`pom.xml`), Gradle
    (`build.gradle[.kts]`, `settings.gradle[.kts]`), PHP (`composer.json/lock`),
    Ruby (`Gemfile[.lock]`), Dart (`pubspec.yaml/lock`), Deno (`deno.json[c]`),
    Bun lockfile (`bun.lockb`).
  - Ambiguous names that may hold committed or user data (`vendor`, `packages`,
    `.terraform`) are intentionally excluded; runtime dirs (`data`, `outputs`,
    `logs`, …) remain REVIEW, never promoted to SAFE.
- Added `.github/workflows/publish.yml`: TestPyPI/PyPI publishing via PyPI Trusted
  Publishing (OIDC) — no API tokens stored. Manual `workflow_dispatch`
  (`target: testpypi | pypi`) for the policy-mandated TestPyPI-first flow, plus
  automatic PyPI publish on a published GitHub Release. Build job runs
  `twine check` on every distribution.
- Added `docs/PUBLISHING.md`: step-by-step trusted-publisher setup for each index
  and a manual `twine` fallback; distribution-surface notes.
- Removed the auto-generated `python-publish.yml` (duplicate of `publish.yml`; both
  triggered on `release: published`, which would double-publish) and `static.yml`
  (deployed the entire repo root to GitHub Pages on every push — no site content for
  a CLI tool). `publish.yml` is the single publishing workflow.
Safety contract of this release:

- The tool scans, plans, verifies, attests, maps explicit evidence, inventories Docker
  read-only, renders reports, and generates synthetic demo workspaces. The only
  mutating cleanup command remains `clean`.
- `clean` removes solely `SAFE` entries of one byte-exact, human-approved plan,
  requires the exact plan hash, re-checks root, symlink/junction/reparse, secret,
  `.git`, and filesystem-boundary guards at delete time, and has no rollback claim.
- The tool does **not** delete Docker volumes, uninstall global packages, mutate
  registry/services/PATH, read shell history, execute scanned repository content,
  or print secret contents.

## v1.0.0

Stable release (explicit maintainer release command, 2026-07-06). No functional change
from v0.9.2; this release aligns the package track with the completed roadmap.

- `pyproject.toml` version `0.8.0` → `1.0.0`; classifier `3 - Alpha` →
  `5 - Production/Stable`.
- Output schemas are now **frozen** at their current versions per
  `docs/SCHEMA_STABILITY.md` (scan 0.1.0, plan/token 0.2.0, action log 0.3.0,
  verify/attestation 0.4.0, evidence 0.5.0, docker 0.6.0, demo/benchmark 0.7.0).
  Breaking changes from here require a new major schema version.
- Docs aligned: README status, roadmap statuses, `SECURITY.md` supported status,
  `docs/RELEASE_POLICY.md` current-state facts (policy rules unchanged).

Safety contract of this release (restated per release policy §3.5):

- The tool scans, plans, verifies, and attests read-only; the only mutating command is
  `clean`, which removes solely `SAFE` entries of one byte-exact, human-approved plan,
  re-checks every guard (root boundary, symlink/junction/reparse point, secret, `.git`,
  filesystem boundary) at delete time, and fail-fasts on error. There is no rollback.
- The tool does **not**: delete Docker volumes, uninstall global packages, touch
  registry/services/PATH, read shell history, execute scanned repository content,
  or print secret contents.
- Tag `v1.0.0` is created on the merge commit of this PR (tag name equals package
  version). Publishing to TestPyPI/PyPI remains a separate, explicitly-commanded step.

## v0.9.2

- Added `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1); reports route through the
  `SECURITY.md` contact channel.
- Roadmap refreshed: v0.9.0/v0.9.1 marked DONE, v0.9.2 community readiness scope
  documented; the feedback loop stays open with triage per `CONTRIBUTING.md`.
- Documentation only; no behavior or schema change.

## v0.9.1

- **Safety fix (audit finding)**: Windows junctions and mount points were not treated
  as link boundaries — `Path.is_symlink()` reports them as False on all supported
  Python versions and `os.walk(followlinks=False)` descends into them. A junction
  planted inside an approved SAFE entry could have redirected removal outside the
  root (a same-volume junction also bypasses the `st_dev` mount check). Confirmed
  empirically on Python 3.11 and 3.13 before the fix.
- New `is_reparse_point()` / `is_link_like()` in `safety/symlink_guard.py` (lstat
  `FILE_ATTRIBUTE_REPARSE_POINT`; POSIX unaffected). Scan now reports junction
  artifacts as link-like with size 0 and never traverses them; clean refuses any
  entry containing a non-symlink reparse point (`SKIPPED_GUARD_FAIL`, fail-safe) and
  the removal walk prunes link-like directories with a defense-in-depth abort.
- Added `docs/THREAT_MODEL.md`: adversary model (scanned repo = untrusted input),
  threat/mitigation/test matrix (T1–T10), the junction audit finding, residual risks.
- Added `tests/test_safety_audit.py`: junction escape containment for size
  estimation, junction artifact flagging, junction planted inside an approved entry,
  entry replaced by a junction, hostile-name scan survival, and a secret-content
  marker sweep across all scan outputs.
- `docs/CLEANER_SAFETY_MODEL.md` and README guard wording aligned (symlink/junction).

## v0.9.0

- Public beta documentation round: `docs/ROADMAP.md` rewritten with per-milestone
  status (v0.1.x–v0.7.x DONE, v0.8.x/v0.9.x in progress, v1.0.0 criteria, permanent
  out-of-scope list).
- Added `docs/SCHEMA_STABILITY.md`: every machine-readable output with its schema
  version field and current value, additive-only compatibility promise until v1.0.0,
  schema freeze at v1.0.0, and the enum contracts (risk classes, plan actions,
  action-log decisions).
- Added an issue triage process to `CONTRIBUTING.md`: safety reports first, then bugs,
  then feature requests; destructive-capability proposals require a dedicated safety
  review issue.
- Documentation only; no behavior or schema change.

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
