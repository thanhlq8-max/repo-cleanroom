# PROJECT_STATE addendum — v0.1.2

STATUS: IMPLEMENTATION_ADDENDUM
PROJECT: Repo Cleanroom
VERSION: v0.1.2-SAMPLE-EVIDENCE-BACKLOG
DATE: 2026-07-03
PRIMARY_MODE: CONTROL

## Scope lock

v0.1.2 is a documentation, sample evidence, and backlog visibility update.

Allowed:

- sample scan output under `examples/sample-scan/`;
- documentation explaining sample evidence;
- README links to sample output;
- roadmap/changelog updates;
- initial GitHub issue backlog.

Forbidden:

- scanner behavior change;
- clean/delete command;
- shell history access;
- Docker mutation;
- global package uninstall;
- registry/service/PATH mutation;
- target repository script execution.

## Repository correction

The repository is no longer `TO_BE_CREATED`.

Current repo:

```text
thanhlq8-max/repo-cleanroom
```

Default branch:

```text
main
```

## Validation gate

Before merge, run:

```powershell
py -m compileall src tests
py -m pytest -q
py -m build
```

CI should run the same validation on Python 3.11, 3.12, and 3.13.

## Next allowed work

After v0.1.2 passes and merges:

```text
v0.1.3 — report usability polish or schema validation tests
```

Do not start v0.2.0 plan engine until v0.1.x scanner/report evidence is stable.
