# PROJECT_STATE addendum — v0.1.4

STATUS: IMPLEMENTATION_ADDENDUM
PROJECT: Repo Cleanroom
VERSION: v0.1.4-WINDOWS-PATH-GUARD-TESTS
DATE: 2026-07-03
PRIMARY_MODE: CONTROL

## Scope lock

v0.1.4 is a path guard test hardening update.

Allowed:

- Expand `tests/test_path_guard.py` coverage.
- Add Windows-focused temporary-directory scenarios.
- Update changelog.

Forbidden:

- Change scanner discovery behavior.
- Add a plan command.
- Add a filesystem removal command.
- Read shell history.
- Mutate Docker, global packages, registry, services, or PATH.
- Execute target repository scripts.

## Issue addressed

- #4: Windows path guard coverage.

## Validation gate

Before merge, run:

```powershell
py -m compileall src tests
py -m pytest -q
py -m build
```

CI should run the same validation on Python 3.11, 3.12, and 3.13.
