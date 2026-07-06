# Cleaner Safety Model (v0.3.0-A Design)

STATUS: DESIGN DOCUMENT — no `clean` command exists and none may be implemented until the
maintainer explicitly accepts this design (roadmap gate: v0.3.0-A precedes any cleaner code).
This document specifies the safety model that a future approval-gated `clean` prototype
(v0.3.0-B) must satisfy. It builds on `docs/CLEANUP_PLAN_SCHEMA.md` (v0.2.0-A) and
`docs/APPROVAL_TOKEN.md` (v0.2.0-B).

## 1. Scope of the future prototype

The v0.3.0-B prototype may remove ONLY:

- entries whose `proposed_action` is `PROPOSE_REMOVE` in one exact approved plan;
- which are risk class `SAFE`;
- which are regular directories/files physically inside the approved `root`;
- which still match the plan record at execution time (existence, non-symlink, in-root).

Everything else is out of scope permanently for the prototype: `REVIEW`, `DANGEROUS`,
`BLOCKED` entries, `.git` directories, anything matched by the secret guard, symlinks and
their targets, and any path outside the plan.

## 2. Preconditions (all required before touching anything)

1. `cleanup_plan.json` exists, parses, and passes the v0.2.2 schema contract.
2. `approval_token.json` exists and passes every verification rule in
   `docs/APPROVAL_TOKEN.md` §4, including exact `plan_hash` match and expiry.
3. The `--root` argument, the plan `root`, and the token `root` are all equal after resolve.
4. The user re-confirms interactively (or via an explicit `--yes-exact-plan <plan_hash>`
   argument that must contain the full plan hash — no blanket `--yes`).
5. Dry-run parity: `--dry-run` must be implemented first (v0.3.1 hardens it) and the real
   run must execute exactly the entry set the dry run reported.

## 3. Per-entry execution guards (re-checked at delete time, not only at plan time)

For each entry, in order, before any removal:

1. Path guard: resolved entry path is strictly inside resolved root.
2. Identity check: path still exists and is still not link-like — a path that became a
   symlink **or any Windows reparse point (junction/mount point)** after planning is
   skipped as `SKIPPED_CHANGED`.
3. Secret guard: path/name re-classified; any protected match aborts that entry as
   `SKIPPED_PROTECTED` (defense in depth; such entries should never be in the proposal set).
4. `.git` guard: entries containing or equal to a `.git` component are refused.
5. Containment: removal is performed bottom-up within the entry directory only; the walker
   must not follow symlinks (`followlinks=False` semantics), must refuse to cross a
   filesystem mount point inside the entry, and must refuse the whole entry when it
   contains a non-symlink reparse point (junction/mount point) — `os.walk` alone does
   not stop at junctions, see `docs/THREAT_MODEL.md` T2.

Any guard failure on an entry skips that entry and records the reason; it never widens to
other entries. Any unexpected exception aborts the whole run after logging.

## 4. Action log and removed manifest (required outputs)

Every run (dry or real) writes into `--out-dir`:

- `clean_action_log.json`: one record per entry — entry_id, decision
  (`REMOVED` / `DRY_RUN_WOULD_REMOVE` / `SKIPPED_CHANGED` / `SKIPPED_PROTECTED` /
  `SKIPPED_GUARD_FAIL` / `ERROR`), timestamps, bytes/file counts observed at execution.
- `removed_manifest.json`: only for real runs — the exact paths removed, for verification
  input in v0.4.x.

The tool must never claim success beyond what the log proves (no "cleaned PC" claims).
Partial completion is reported as partial with per-entry status.

## 5. Failure and recovery policy

- No rollback is claimed or implemented in the prototype. Removal is destructive; the
  mitigation is the narrow SAFE-only scope, exact-plan binding, and dry-run parity.
- On first `ERROR` decision the run stops (fail-fast) rather than continuing blind.
- A partially executed plan cannot be resumed: the workspace changed, so the plan hash no
  longer represents reality. The user must rescan → replan → reapprove.

## 6. Test obligations before v0.3.0-B may merge

- Root guard: attempts to escape via `..`, junctions, and symlinks are refused (extend the
  v0.1.4 path guard suite to the cleaner path).
- Symlink refusal: SAFE symlink entries are never removed; targets never touched.
- Secret guard: planted `.env`/key-like files inside a SAFE directory abort that entry.
- Approval binding: modified plan byte → token invalid → zero removals.
- Expiry: expired token → zero removals.
- Dry-run parity: dry-run and real-run entry sets are identical on an unchanged workspace.
- No-widening: entries added to the workspace after planning are never touched.

## 7. Explicit non-goals

- No recursive "clean everything under root" mode. Only plan entries.
- No configuration option that relaxes any guard.
- No deletion of Docker objects, global packages, registry keys, services, or anything
  reachable only through a symlink.

## 8. Acceptance

Implementation of v0.3.0-B may begin only after the maintainer reviews this document and
accepts it by PR number in a recorded decision. Until then the codebase must contain no
removal capability, and CI-tested contracts (v0.2.2) keep the plan pipeline PLAN_ONLY.
