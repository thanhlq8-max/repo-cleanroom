# Output Schema Stability

Status: public beta (v0.9.0). This document declares which machine-readable outputs
exist, the schema version each one carries, and what stability consumers can rely on.

## Stability promise

- Every JSON output embeds its own schema version field (table below). Consumers should
  dispatch on that field, not on the package version.
- From v0.9.0 until v1.0.0: schema changes are **additive only** (new optional fields).
  No field is renamed, removed, or re-typed; no enum value changes meaning.
- At v1.0.0 the schema versions below are frozen. Any breaking change afterwards
  requires a new major schema version and a changelog entry.
- Enum contracts that never change within a major version:
  - risk classes: `SAFE`, `REVIEW`, `DANGEROUS`, `BLOCKED`;
  - plan actions: `PROPOSE_REMOVE`, `REVIEW_REQUIRED`, `NO_ACTION`, `FORBIDDEN`;
  - action-log decisions: `REMOVED`, `DRY_RUN_WOULD_REMOVE`, `SKIPPED_CHANGED`,
    `SKIPPED_PROTECTED`, `SKIPPED_GUARD_FAIL`, `ERROR`, `NOT_PROPOSED`, `NOT_PROCESSED`.

## Output files and schema versions

| Output file | Producing command | Version field | Current version |
|---|---|---|---|
| `inventory.json`, `artifact_inventory.json`, `public_safety_check.json`, `schema_version.json` | `scan` | `schema_version` | `0.1.0` |
| `cleanup_plan.json` | `plan` | `plan_schema_version` | `0.2.0` |
| `approval_token.json` | `approve` | `token_schema_version` | `0.2.0` |
| `clean_action_log.json`, `removed_manifest.json` | `clean` | `log_schema_version` | `0.3.0` |
| `verify.json` | `verify` | `verify_schema_version` | `0.4.0` |
| `attestation.json` | `attest` | `attestation_schema_version` | `0.4.0` |
| `command_evidence.json` | `evidence` | `evidence_schema_version` | `0.5.0` |
| `docker_inventory.json` | `docker-scan` | `docker_inventory_schema_version` | `0.6.0` |
| `docker_cleanup_plan.json` | `docker-plan` | `docker_plan_schema_version` | `0.6.0` |
| `demo_manifest.json` | `demo-workspace` | `demo_schema_version` | `0.7.0` |
| `benchmark_results.json` | `scripts/benchmark_scan.py` | `benchmark_schema_version` | `0.7.0` |

Markdown/HTML outputs (`findings.md`, `cleanup_plan.md`, `clean_report.md`,
`final_report.md`, `evidence_map.md`, `findings.html`) are human-facing renderings of
the JSON files above. Their layout may improve between releases; only the JSON files
are a machine contract.

## Compatibility notes

- Schema versions are decoupled from the package version on purpose
  (see `docs/RELEASE_POLICY.md`): a package release without schema changes keeps
  every schema version unchanged.
- Detailed field-level contracts: `docs/CLEANUP_PLAN_SCHEMA.md` (plan),
  `docs/APPROVAL_TOKEN.md` (token). Scan/report fields are demonstrated in
  `examples/sample-scan/` and pinned by contract tests under `tests/`.
