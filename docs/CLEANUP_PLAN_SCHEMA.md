# cleanup_plan.json Schema (v0.2.0-A Design)

STATUS: DESIGN DOCUMENT — no `plan` command exists yet. This document defines the schema
that a future `repo-cleanroom plan` command (v0.2.1) would emit. Nothing in v0.2.x removes
files. Plan generation is a read-only transformation of an existing `artifact_inventory.json`
into a reviewable proposal document.

Schema version described here: `plan_schema_version = "0.2.0"`.

## 1. Purpose

A cleanup plan is the reviewable, hashable contract between what the scanner found and what
a future, approval-gated `clean` command (v0.3.x, not designed here) would be allowed to do.
The plan must be:

- **Derived**: generated only from a named `artifact_inventory.json`, never from a live rescan.
- **Reviewable**: a human can read every entry and see path, risk, proposed action, and reason.
- **Bindable**: a reserved `plan_hash` field allows a future approval token to bind to this
  exact plan content (see `docs/APPROVAL_TOKEN.md`, v0.2.0-B).
- **Non-executable**: the plan is data. It grants no permission by itself.

## 2. Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `plan_id` | string (UUIDv4) | yes | Unique id for this generated plan. |
| `plan_schema_version` | string | yes | Schema version of this document, `"0.2.0"`. |
| `generated_at_utc` | string (ISO 8601, UTC offset) | yes | Plan generation timestamp. |
| `mode` | string | yes | Always `"PLAN_ONLY"` in v0.2.x. |
| `root` | string | yes | The exact root path the source scan used. Copied from the inventory, never recomputed. |
| `source_artifact_inventory` | object | yes | Provenance of the input inventory (see 2.1). |
| `entries` | array of Entry | yes | One entry per artifact in the source inventory. No artifact may be silently dropped. |
| `summary` | object | yes | Aggregated counts/bytes (see 2.2). |
| `plan_hash` | string or null | yes (nullable) | RESERVED. `null` in v0.2.1. Future: SHA-256 over the canonical plan payload (see 5). |

### 2.1 `source_artifact_inventory`

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Path of the `artifact_inventory.json` used as input. |
| `schema_version` | string | yes | `schema_version` value copied from that inventory. |
| `sha256` | string | yes | SHA-256 hex digest of the inventory file bytes. Plans are invalid if the inventory changes. |

### 2.2 `summary`

| Field | Type | Required | Description |
|---|---|---|---|
| `total_entries` | int | yes | Must equal `len(entries)`. |
| `proposed_remove_count` | int | yes | Entries with `proposed_action = "PROPOSE_REMOVE"`. |
| `proposed_remove_bytes` | int | yes | Sum of `size_bytes` over those entries. |
| `review_required_count` | int | yes | Entries with `proposed_action = "REVIEW_REQUIRED"`. |
| `blocked_count` | int | yes | Entries with `proposed_action = "FORBIDDEN"`. |
| `no_action_count` | int | yes | Entries with `proposed_action = "NO_ACTION"`. |
| `by_risk` | object | yes | Count per risk class, same convention as inventory `totals.by_risk`. |

## 3. Entry fields

Each entry mirrors one artifact record and adds the plan decision:

| Field | Type | Required | Description |
|---|---|---|---|
| `entry_id` | string | yes | Stable within the plan: `"<repo_relative_path>/<relative_path>"`. |
| `repo_name` | string | yes | Copied from inventory. |
| `repo_relative_path` | string | yes | Copied from inventory. |
| `relative_path` | string | yes | Copied from inventory. |
| `path` | string | yes | Absolute path copied from inventory. Must resolve inside `root` (path guard re-checked at plan time). |
| `artifact_type` | string | yes | Copied from inventory. |
| `risk` | string | yes | `SAFE` / `REVIEW` / `DANGEROUS` / `BLOCKED`, copied from inventory. |
| `size_bytes` | int | yes | Copied from inventory. |
| `file_count` | int | yes | Copied from inventory. |
| `is_symlink` | bool | yes | Copied from inventory. Symlinks are never `PROPOSE_REMOVE`. |
| `proposed_action` | string | yes | See action mapping (4). |
| `reason` | string | yes | Human-readable justification for the proposed action. |

## 4. Action mapping (fixed policy, not configurable in v0.2.x)

| Risk | `proposed_action` | Meaning |
|---|---|---|
| `SAFE` (and not symlink) | `PROPOSE_REMOVE` | Candidate for a future approved clean. Still deletes nothing. |
| `SAFE` (symlink) | `NO_ACTION` | Symlinked artifacts are excluded from proposals. |
| `REVIEW` | `REVIEW_REQUIRED` | User must inspect manually; never auto-promoted to removal by the tool. |
| `DANGEROUS` | `NO_ACTION` | Out of scope for any v0.3.x clean prototype. |
| `BLOCKED` | `FORBIDDEN` | Must never be removed; listed so review is complete. |

Rules:

- Every artifact from the source inventory appears exactly once — including `BLOCKED` and
  `REVIEW` items. Completeness is a review feature, not an execution list.
- `FORBIDDEN` and `REVIEW_REQUIRED` entries exist so the "blocked items" and
  "review-required items" are explicit in the plan itself (queryable via
  `proposed_action`), not implied by absence.
- A plan generator MUST fail (no partial plan) if any inventory record is malformed or if
  any `path` fails the root path guard.

## 5. `plan_hash` (reserved)

- `null` in v0.2.1 output.
- Future definition (locked here for design purposes): SHA-256 hex digest of the plan JSON
  serialized canonically (UTF-8, sorted keys, `plan_hash` field set to `null`, no
  insignificant whitespace). This makes the hash stable and verifiable by third parties.
- The approval token design (`docs/APPROVAL_TOKEN.md`) binds to this hash. Any change to any
  plan byte invalidates any approval.

## 6. Safety invariants

1. Plan generation reads exactly two things: the named inventory file and (for the path
   guard re-check) the filesystem path structure. It never executes repo content.
2. Plan generation writes exactly two files into `--out-dir`: `cleanup_plan.json` and
   `cleanup_plan.md` (human-readable rendering). No other side effects.
3. No file removal capability may be introduced in v0.2.x. `mode` is always `"PLAN_ONLY"`.
4. A plan is not permission. Execution requires the future v0.3.x approval-token flow.

## 7. Sample

A complete synthetic sample derived from `examples/sample-scan/artifact_inventory.json` is
committed at `examples/sample-plan/cleanup_plan.json`.
