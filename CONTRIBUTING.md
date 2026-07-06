# Contributing

Repo Cleanroom is safety-critical because it can remove local files. Contributions must preserve the safety model. All community interaction follows [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

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

## Issue triage

Issues are triaged in this priority order:

1. **Safety reports** — anything where the tool could touch data it must not touch
   (path escape, symlink/junction traversal, secret exposure, deletion outside an
   approved plan). Use the *safety review* issue template. These take precedence over
   all feature work. Suspected security vulnerabilities go through `SECURITY.md`
   instead of a public issue.
2. **Bugs** — wrong scan/plan/verify output, crashes, incorrect exit codes. Use the
   *bug report* template and include the command line, OS, and Python version.
3. **Feature requests** — use the *feature request* template. Proposals that add or
   widen destructive capability are only accepted with a dedicated safety review issue
   and must fit the roadmap gates in `docs/ROADMAP.md`.

Triage outcomes: an issue is either accepted (assigned to a roadmap milestone),
needs-info (reporter asked for reproduction details), or declined with the reason —
typically because it conflicts with the safety model (`docs/SAFETY_MODEL.md`) or the
permanently-out-of-scope list in the roadmap.
