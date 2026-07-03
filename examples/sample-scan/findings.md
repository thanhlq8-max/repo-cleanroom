# Repo Cleanroom Findings

STATUS: READ_ONLY_SCAN_COMPLETE

## Summary

- Root: `C:\Users\demo\GitHub`
- Repositories scanned: 3
- Artifacts found: 7
- Estimated artifact size: 235.5 MB
- Cleanup performed: NO
- Shell history read: NO
- Target repo scripts executed: NO

## Risk counts

| Risk | Count |
|---|---:|
| SAFE | 5 |
| REVIEW | 1 |
| DANGEROUS | 0 |
| BLOCKED | 1 |

## Repositories

| Repo | Relative path | Manifests |
|---|---|---:|
| `demo-python-tool` | `demo-python-tool` | 2 |
| `demo-node-app` | `demo-node-app` | 2 |
| `demo-rust-cli` | `demo-rust-cli` | 1 |

## Artifact findings

| Risk | Type | Size | Repo-local path | Reason |
|---|---|---:|---|---|
| SAFE | `python_virtualenv` | 30.0 MB | `demo-python-tool/.venv` | common repo-local generated artifact |
| SAFE | `python_cache` | 2.0 KB | `demo-python-tool/.pytest_cache` | common repo-local generated artifact |
| BLOCKED | `protected_config` | 42 B | `demo-python-tool/.env` | protected sensitive path/name pattern |
| SAFE | `node_dependencies` | 150.0 MB | `demo-node-app/node_modules` | common repo-local generated artifact |
| SAFE | `build_output` | 7.0 MB | `demo-node-app/dist` | common repo-local generated artifact |
| REVIEW | `runtime_logs` | 512.0 KB | `demo-node-app/logs` | may contain user/runtime data; requires review |
| SAFE | `rust_build_output` | 48.0 MB | `demo-rust-cli/target` | common repo-local generated artifact |

## Safety notes

- v0.1.0 is read-only and does not delete files.
- Detection does not equal deletion approval.
- `BLOCKED` items must not be auto-deleted or printed as content.
- Symlink targets are not traversed for size estimation.
