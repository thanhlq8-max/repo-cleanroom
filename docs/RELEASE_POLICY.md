# Release and Version Policy

STATUS: POLICY_v1 — applies from v0.1.6 onward. Changing this policy requires a dedicated PR.

## 1. Two version tracks

Repo Cleanroom currently uses two version tracks:

| Track | Where | Current value | Meaning |
|---|---|---|---|
| Milestone version | CHANGELOG.md, PR/branch names, project state | v0.1.x per merged PR | Process/scope increments (docs, tests, hardening) |
| Package version | `pyproject.toml` `project.version` | `0.1.0` | The installable artifact version |

This split is intentional during pre-release development. Milestone versions may advance
without a package release, because most v0.1.x increments change docs, tests, or process —
not installable behavior.

## 2. Alignment decision

- The package version in `pyproject.toml` is **not** bumped automatically when a milestone
  version advances.
- The two tracks are aligned only in an explicit release task (roadmap Phase H, v0.8.0
  "Version Alignment"), or earlier if the maintainer explicitly orders a release.
- Any PR that changes `project.version` must contain the word `release` in its branch name
  and say so in the PR title. Version changes hidden inside unrelated PRs are invalid.

## 3. When a package release is allowed

A package release (TestPyPI or PyPI) requires ALL of:

1. An explicit maintainer command in that session. No autonomous publishing.
2. `pyproject.toml` version, `CHANGELOG.md`, git tag, and README wording aligned to the
   same version in one release PR.
3. CI green on the release PR (Windows, Python 3.11/3.12/3.13).
4. `py -m build` producing sdist and wheel without errors.
5. The safety contract restated in the release notes: current version scope
   (read-only for all v0.1.x/v0.2.x releases) and explicit list of what the tool does not do.

## 4. Version number semantics (pre-1.0)

- `0.MINOR.PATCH` while pre-1.0.
- MINOR marks a capability phase boundary (per the public roadmap): 0.1 read-only scan,
  0.2 plan design/generation without deletion, 0.3 approval-gated clean, and onward.
- PATCH marks hardening, docs, tests, and report improvements inside a phase.
- No version may claim a capability phase it does not implement. A version that cannot
  delete anything must not be described as a cleanup release.

## 5. Pre-release checklist (to copy into any future release PR)

```text
[ ] Explicit maintainer release command recorded
[ ] pyproject version bumped intentionally in this PR only
[ ] CHANGELOG entry for the released version is complete
[ ] Git tag name equals package version
[ ] CI green on Python 3.11 / 3.12 / 3.13 (windows-latest)
[ ] py -m compileall src tests clean
[ ] py -m pytest -q all pass
[ ] py -m build produces sdist + wheel
[ ] README/docs wording matches actual capability (no cleanup overclaim)
[ ] Sample/evidence files are synthetic or sanitized
[ ] No destructive command exists outside the approved roadmap gates
```

## 6. Current state under this policy

- `pyproject.toml` stays at `0.1.0` until the first intentional release task.
- Milestone versions continue to advance via CHANGELOG.md and PR scope names.
- No TestPyPI/PyPI publication is scheduled; it requires an explicit maintainer command.
