# Approval Token (v0.2.0-B Design)

STATUS: DESIGN DOCUMENT — no approval or clean capability exists yet. This document defines
how a future `clean` command (v0.3.x, not designed here) would verify that a human approved
one exact cleanup plan. Nothing in v0.2.x creates, consumes, or acts on approval tokens.

Depends on: `docs/CLEANUP_PLAN_SCHEMA.md` (v0.2.0-A), specifically the canonical
`plan_hash` definition reserved there.

## 1. Principle: exact-plan binding

An approval is a statement about one specific byte-exact plan, not about a root, a repo, or
a "kind of cleanup". The token therefore binds to the plan's canonical SHA-256 hash. If any
byte of the plan changes — one more entry, one changed path, one edited reason string — the
hash changes and every previously issued approval is invalid. There is no partial,
transferable, or renewable approval.

## 2. Token fields

`approval_token.json`:

| Field | Type | Required | Description |
|---|---|---|---|
| `token_schema_version` | string | yes | `"0.2.0"`. |
| `plan_id` | string | yes | Copied from the approved plan. Convenience only; the binding field is `plan_hash`. |
| `plan_hash` | string | yes | Canonical SHA-256 of the approved plan (per CLEANUP_PLAN_SCHEMA.md §5). THE binding field. |
| `root` | string | yes | Must equal the plan's `root`. Defense in depth against applying a plan to another tree. |
| `entry_count` | int | yes | Must equal the plan's `summary.total_entries`. |
| `approved_action` | string | yes | Always `"REMOVE_PROPOSED_SAFE"` — the only approvable action class in this design. |
| `approved_risk_classes` | array of string | yes | Must be exactly `["SAFE"]`. `REVIEW`/`DANGEROUS`/`BLOCKED` are not approvable values; a token listing them is invalid by schema. |
| `approved_remove_count` | int | yes | Must equal `summary.proposed_remove_count`. |
| `approved_remove_bytes` | int | yes | Must equal `summary.proposed_remove_bytes`. |
| `approved_at_utc` | string | yes | ISO 8601 UTC timestamp of the human approval. |
| `expires_at_utc` | string | yes | Hard expiry. Proposal: 24 hours after approval; stale workspaces must be rescanned and replanned. |
| `approved_by` | string | yes | Free-form operator identity string (local tool: self-attested, no PII requirement). |

## 3. Issuance (future flow, for context only)

1. User runs the future `plan` command → `cleanup_plan.json` with computed `plan_hash`.
2. User reviews `cleanup_plan.md`.
3. User explicitly issues approval (future `approve` interaction, undesigned) → tool writes
   `approval_token.json` next to the plan. The tool never self-issues a token.

## 4. Verification rules (all must pass before any future clean acts)

1. Token parses and `token_schema_version` is supported.
2. Recompute the plan's canonical hash from `cleanup_plan.json` → must equal `plan_hash`.
3. `root` equals the plan's `root`, and equals the `--root` given to the future clean command.
4. `entry_count`, `approved_remove_count`, `approved_remove_bytes` equal the plan's summary.
5. `approved_risk_classes == ["SAFE"]` and `approved_action == "REMOVE_PROPOSED_SAFE"`.
6. Current time is before `expires_at_utc`.
7. Even with a valid token, execution-time guards still apply per entry: path guard inside
   root, symlink refusal, secret guard, and skip of anything not `PROPOSE_REMOVE` in the
   plan. A token can only narrow, never widen, what the plan proposed.

Any rule failing → refuse with a specific error, delete nothing, exit non-zero.

## 5. Invalidation

An approval token is invalid when:

- the plan file was modified after approval (hash mismatch — the primary mechanism);
- the source inventory named in the plan changed (its `sha256` no longer matches, which
  requires replanning, which changes the plan hash);
- it is past `expires_at_utc`;
- any count/byte field disagrees with the plan;
- it approves anything other than exactly `["SAFE"]` / `"REMOVE_PROPOSED_SAFE"`.

There is no revocation list: to revoke, delete the token file; to re-approve, re-run the
approval flow against the regenerated plan.

## 6. Explicit non-goals of this design

- No network, no account, no signing service. Local file, local trust model.
- No delegation: a token cannot authorize future plans, other roots, or other machines.
- No override channel for `BLOCKED`/`DANGEROUS`/`REVIEW` items. A future exception process,
  if ever proposed, requires its own safety-review issue and design gate (G2).
