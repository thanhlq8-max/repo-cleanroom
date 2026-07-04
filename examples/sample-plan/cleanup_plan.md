# Repo Cleanroom Cleanup Plan (PLAN_ONLY)

STATUS: PLAN_ONLY — this plan is a proposal document. Nothing was deleted.

## Summary

- Plan id: `6f1c2b9a-3d47-4e21-9c58-0a8f4d5e7b10`
- Root: `C:\Users\demo\GitHub`
- Source inventory: `C:\Users\demo\GitHub\.cleanroom\artifact_inventory.json`
- Total entries: 7
- Proposed for future removal: 5 (235.0 MB)
- Review required: 1
- Forbidden (protected): 1
- No action: 0
- Files removed by this plan: NONE

## Proposed for future approved removal (5 entry(ies), 235.0 MB)

| Risk | Type | Size | Entry | Reason |
|---|---|---:|---|---|
| SAFE | `node_dependencies` | 150.0 MB | `demo-node-app/node_modules` | SAFE repo-local generated artifact; candidate for future approved clean |
| SAFE | `rust_build_output` | 48.0 MB | `demo-rust-cli/target` | SAFE repo-local generated artifact; candidate for future approved clean |
| SAFE | `python_virtualenv` | 30.0 MB | `demo-python-tool/.venv` | SAFE repo-local generated artifact; candidate for future approved clean |
| SAFE | `build_output` | 7.0 MB | `demo-node-app/dist` | SAFE repo-local generated artifact; candidate for future approved clean |
| SAFE | `python_cache` | 2.0 KB | `demo-python-tool/.pytest_cache` | SAFE repo-local generated artifact; candidate for future approved clean |

## Requires manual review (1 entry(ies), 512.0 KB)

| Risk | Type | Size | Entry | Reason |
|---|---|---:|---|---|
| REVIEW | `runtime_logs` | 512.0 KB | `demo-node-app/logs` | may contain user/runtime data; manual inspection required |

## Forbidden (protected items) (1 entry(ies), 42 B)

| Risk | Type | Size | Entry | Reason |
|---|---|---:|---|---|
| BLOCKED | `protected_config` | 42 B | `demo-python-tool/.env` | protected sensitive path/name pattern; must never be removed or printed |

## Safety notes

- A plan is not permission. No file is removed by generating or reading it.
- Future removal requires the approval-token flow (docs/APPROVAL_TOKEN.md) in v0.3.x.
- FORBIDDEN entries must never be removed under any flow.
- REVIEW_REQUIRED entries are never auto-promoted to removal by the tool.

