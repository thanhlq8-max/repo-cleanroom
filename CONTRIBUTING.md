# Contributing

Repo Cleanroom is safety-critical because later versions will remove local files. Contributions must preserve the safety model.

## Rules

- No destructive behavior without a plan, approval, and verification gate.
- No registry, service, scheduled task, PATH, global package, or Docker volume mutation in MVP.
- No target repo script execution during scan/plan/clean/verify.
- No secret content logging.
- Tests are required for path safety, secret blocking, and risk classification.

## Local checks

```powershell
py -m compileall src tests
py -m pytest -q
py -m build
```
