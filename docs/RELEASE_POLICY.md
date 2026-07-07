# Release and Version Policy

STATUS: POLICY_v1 — applies from v0.1.6 onward. Changing this policy requires a dedicated PR.

## 1. Two version tracks

Repo Cleanroom currently uses two version tracks:

| Track | Where | Current value | Meaning |
|---|---|---|---|
| Milestone version | CHANGELOG.md, PR/branch names, project state | v1.0.0 | Process/scope increments (docs, tests, hardening) |
| Package version | `pyproject.toml` `project.version` | `1.0.0` | The installable artifact version |

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

## 4. Version number semantics

Pre-1.0 (historical):

- `0.MINOR.PATCH`: MINOR marked a capability phase boundary (0.1 read-only scan,
  0.2 plan generation without deletion, 0.3 approval-gated clean, and onward);
  PATCH marked hardening, docs, tests, and report improvements inside a phase.

From 1.0.0 (semver):

- MAJOR: breaking change to a frozen output schema or to the safety contract surface.
- MINOR: new capability behind the existing safety gates; additive schema fields only.
- PATCH: fixes, docs, tests, hardening. Safety fixes are always at least a PATCH release.
- Unchanged rule: no version may claim a capability it does not implement.

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

- Tracks aligned at `1.0.0` (explicit release tasks: v0.8.0 on 2026-07-05,
  v1.0.0 on 2026-07-06). Tags `v0.8.0` and `v1.0.0` mark the respective merge commits.
- Milestone versions continue to advance via CHANGELOG.md and PR scope names.
- Each publication step still requires an explicit maintainer command (§3 rule 1 is
  permanent). Mechanics are documented in `docs/PUBLISHING.md`; the
  `.github/workflows/publish.yml` workflow is the recommended path (TestPyPI dry run
  first via manual dispatch, then PyPI). Running that workflow, or cutting a GitHub
  Release, is the explicit maintainer action — the workflow never triggers itself.
