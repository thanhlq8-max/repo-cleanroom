# Repo Cleanroom Roadmap

Repo Cleanroom follows a safety-gated workflow:

```text
SCAN -> EVIDENCE MAP -> USER-APPROVED PLAN -> CLEAN -> VERIFY -> ATTESTATION REPORT
```

Status legend: **DONE** (merged to `main`, CI-tested) · **IN PROGRESS** · **PLANNED**.

## v0.1.x — scanner foundation — DONE

- read-only scan, repository discovery, manifest detection;
- repo-local artifact detection with risk classification (`SAFE`/`REVIEW`/`DANGEROUS`/`BLOCKED`);
- JSON/Markdown reports, risk-grouped findings;
- CI (windows-latest × Python 3.11/3.12/3.13), contribution templates;
- public sample scan evidence (`examples/sample-scan/`, `docs/SAMPLE_SCAN_EVIDENCE.md`);
- path-guard and symlink-guard test hardening;
- Windows quickstart transcripts.

## v0.2.x — cleanup plan engine — DONE

- `cleanup_plan.json` schema (`docs/CLEANUP_PLAN_SCHEMA.md`) and approval-token design
  (`docs/APPROVAL_TOKEN.md`);
- `plan` command (PLAN_ONLY — removes nothing), risk-grouped plan summary,
  blocked item list, canonical plan hash;
- plan contract tests.

## v0.3.x — approval-gated SAFE clean — DONE

- `approve` command: token bound to the exact plan bytes, SAFE-only, 24 h expiry;
- `clean` command: acts solely on `PROPOSE_REMOVE` SAFE entries of one approved plan,
  re-checks every guard (root boundary, symlink, secret, `.git`, filesystem boundary)
  at delete time, fail-fast, one action-log record per entry;
- `--dry-run`, `clean_report.md`, explicit no-rollback policy
  (`docs/CLEANER_SAFETY_MODEL.md`).

## v0.4.x — verification and attestation — DONE

- `verify` command: read-only filesystem-vs-plan/log comparison (`verify.json`);
- `attest` command: `attestation.json` + `final_report.md` with cleaned / skipped /
  failed / blocked / unchanged categories;
- failed verification is attested as a discrepancy, never as a clean state.

## v0.5.x — explicit command evidence mapping — DONE

- privacy contract first (`docs/COMMAND_EVIDENCE_PRIVACY.md`): no shell-history access
  ever, explicit `--evidence-file` input only, mandatory sanitization, no execution;
- `evidence` command: informational mapping of supplied commands to detected artifacts.

## v0.6.x — Docker read-only scan/plan — DONE

- `docker-scan`: fixed whitelist of read-only `docker` CLI queries, no mutation capability;
- `docker-plan`: informational only, volumes are never proposed for deletion,
  `tool_can_execute_this_plan: false`.

## v0.7.x — review UX and reproducibility — DONE

- `html-report`: static, self-contained, script-free findings page with HTML escaping;
- `demo-workspace`: synthetic try-it workspace, refuses non-empty target directories;
- reproducible scan/plan benchmark with measured results (`docs/PERFORMANCE.md`).

## v0.8.x — packaging and release readiness — DONE

- v0.8.0 — DONE: package version aligned to the milestone track (`pyproject.toml` 0.8.0),
  stale wording aligned with actual capabilities, release policy checklist
  (`docs/RELEASE_POLICY.md`).
- TestPyPI / PyPI publication is tracked post-1.0 (explicit maintainer command
  required for each step; see `docs/RELEASE_POLICY.md` §3).

## v0.9.x — public beta stabilization — DONE

- v0.9.0 — DONE: stable CLI docs, output schema stability statement
  (`docs/SCHEMA_STABILITY.md`), issue triage process (`CONTRIBUTING.md`).
- v0.9.1 — DONE: safety threat model (`docs/THREAT_MODEL.md`), junction/reparse-point
  boundary fix, malicious repo fixture tests, symlink/junction regression tests.
- v0.9.2 — DONE: community readiness — `CODE_OF_CONDUCT.md`, triage process
  live per `CONTRIBUTING.md`, roadmap refreshed. The feedback loop itself stays open:
  incoming issues are triaged against the safety contract on arrival.

## v1.0.0 — stable public release — DONE

All release criteria met:

- stable schemas — **frozen** at their shipped values (`docs/SCHEMA_STABILITY.md`);
- documented safety model, threat model, and privacy contract;
- Windows-first validation evidence (quickstart transcripts, CI green on
  Python 3.11/3.12/3.13);
- public examples for scan and plan outputs;
- no destructive defaults: removal only behind plan + exact-plan approval token,
  volumes/global packages/registry/services never touched.

Post-1.0: PyPI publication (explicit maintainer command per step), then maintenance —
safety reports first, additive improvements behind the same gates.

## v1.1.0 — additive scan coverage and distribution readiness — DONE

- broader built-in artifact and manifest detection across Node, Python, JVM, PHP,
  Ruby, Dart, Deno, and Bun ecosystems;
- nested / monorepo artifact detection with bounded, link-aware traversal;
- cross-platform CI on Ubuntu, Windows, and macOS to exercise POSIX symlink safety
  paths as well as Windows-first behavior;
- explicit `scan --config <file.toml>` support for operator-controlled ignore globs
  and REVIEW-only custom artifact names;
- TestPyPI/PyPI trusted-publishing workflow and publishing guide.

All changes are additive. Frozen output schema version fields remain unchanged, and
the approval-gated cleanup safety contract is unchanged.

## Permanently out of scope

- PC optimization, malware scanning, registry cleaning;
- Docker volume deletion, global package uninstall;
- shell history reading;
- executing scripts from scanned repositories.
