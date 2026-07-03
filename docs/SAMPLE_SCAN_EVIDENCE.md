# Sample scan evidence

This document explains the sample scan artifacts in `examples/sample-scan/`.

The sample is synthetic and intentionally uses a fake Windows path:

```text
C:\Users\demo\GitHub
```

It demonstrates how Repo Cleanroom reports a workspace containing three cloned repositories:

| Repo | Ecosystem | Example artifacts |
|---|---|---|
| `demo-python-tool` | Python | `.venv`, `.pytest_cache`, `.env` |
| `demo-node-app` | Node.js | `node_modules`, `dist`, `logs` |
| `demo-rust-cli` | Rust | `target` |

## Files

```text
examples/sample-scan/schema_version.json
examples/sample-scan/inventory.json
examples/sample-scan/artifact_inventory.json
examples/sample-scan/findings.md
examples/sample-scan/public_safety_check.json
```

## Safety interpretation

The sample shows the core v0.1.0 contract:

- scan mode is `READ_ONLY_SCAN`;
- cleanup is not performed;
- shell history is not read;
- target repository scripts are not executed;
- `.env` is classified as `BLOCKED` by path/name only;
- `node_modules`, `.venv`, `.pytest_cache`, `dist`, and `target` are `SAFE` findings, but not deleted;
- `logs` is `REVIEW` because it may contain user/runtime data.

## What this is not

The sample is not a cleanup plan. It does not approve deletion.

Future versions must still implement:

```text
SCAN -> EVIDENCE MAP -> USER-APPROVED PLAN -> CLEAN -> VERIFY -> ATTESTATION REPORT
```

v0.1.2 only adds public sample evidence and project backlog visibility.
