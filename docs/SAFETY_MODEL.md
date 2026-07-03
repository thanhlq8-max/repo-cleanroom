# Safety Model

Repo Cleanroom is designed around evidence, approval, and verification.

v0.1.0 implements only the read-only scan/report phase.

## Hard safety rules

- No deletion in v0.1.0.
- No target repo script execution.
- No shell history access.
- No registry/service/scheduled-task/PATH mutation.
- No global package uninstall.
- No Docker deletion.
- No symlink traversal during size estimation.
- No secret file content reading.

## Future cleanup gate

A future cleanup command must require:

1. scan report;
2. cleanup plan;
3. risk classification;
4. explicit approval;
5. post-clean verification.

## Risk classes

- `SAFE`: common generated repo-local artifact.
- `REVIEW`: may contain user or runtime data.
- `DANGEROUS`: external/system/high-impact object.
- `BLOCKED`: protected sensitive item.
