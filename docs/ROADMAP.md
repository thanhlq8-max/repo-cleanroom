# Repo Cleanroom Roadmap

Repo Cleanroom follows a safety-gated workflow:

```text
SCAN -> EVIDENCE MAP -> USER-APPROVED PLAN -> CLEAN -> VERIFY -> ATTESTATION REPORT
```

## v0.1.x — scanner foundation

Status: active.

Scope:

- read-only scan;
- repository discovery;
- manifest detection;
- repo-local artifact detection;
- risk classification;
- JSON/Markdown reports;
- CI and GitHub contribution templates;
- public sample scan evidence;
- initial issue backlog.

Forbidden in v0.1.x:

- file deletion;
- package uninstall;
- Docker prune;
- shell history reading;
- registry/service/PATH mutation.

### v0.1.2 — sample evidence and backlog

Goal: make the repo understandable to new visitors without requiring a local install first.

Deliverables:

- `examples/sample-scan/` synthetic scan output;
- `docs/SAMPLE_SCAN_EVIDENCE.md` explanation;
- initial GitHub issue backlog for v0.1.x and v0.2.0;
- no scanner behavior change.

## v0.2.0 — cleanup plan engine

Goal: produce a reviewable cleanup plan without deleting anything.

Required outputs:

- `cleanup_plan.json`;
- risk-grouped plan summary;
- approval hash or equivalent approval token;
- blocked item list;
- plan validation tests.

No deletion is allowed in v0.2.0.

## v0.3.0 — SAFE repo-local clean

Goal: remove only explicitly approved `SAFE` repo-local artifacts.

Required gates:

- plan must exist;
- user approval must match plan;
- path guard must prove every target is inside root;
- symlink targets must not be followed;
- post-clean verification must run.

Still forbidden:

- Docker volumes;
- global packages;
- registry/service mutation;
- `.git` deletion;
- secrets/config deletion.

## v0.4.0 — verification and attestation

Goal: provide a post-clean proof artifact.

Required outputs:

- `verify.json`;
- `attestation.json`;
- `final_report.md`;
- failed-removal list;
- unchanged blocked-item list.

## v0.5.0 — explicit command evidence mapping

Goal: map prior commands to likely artifacts only when the user explicitly opts in.

Required constraints:

- no default shell history reading;
- sanitized command evidence;
- no secret printing;
- no automatic execution of detected commands.

## v0.6.0 — Docker scan/plan

Goal: identify Docker objects linked to a workspace or compose project.

Required constraints:

- scan/plan first;
- no volume deletion by default;
- destructive Docker operations require explicit per-object approval.

## v1.0.0 — stable public release

Required:

- stable schemas;
- documented safety model;
- Windows-first validation evidence;
- public examples;
- CI green across supported Python versions;
- no destructive defaults.
