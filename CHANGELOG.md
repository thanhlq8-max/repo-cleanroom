# Changelog

## v0.1.7

- Grouped the `findings.md` artifact findings section by risk class (`SAFE` → `REVIEW` → `DANGEROUS` → `BLOCKED`) with per-group count and size subtotal.
- Sorted findings inside each risk group by size, largest first.
- Added tests for group ordering, subtotals, and omission of empty groups.
- Report rendering change only; no scan/filesystem side effect change.

## v0.1.6

- Added `docs/RELEASE_POLICY.md`: milestone-vs-package version tracks, alignment rule, release gates, and pre-release checklist.
- Recorded that `pyproject.toml` stays at `0.1.0` until an explicit release task.
- Documentation only; no scanner behavior change.
- No package published.

## v0.1.5

- Added `docs/WINDOWS_QUICKSTART.md` with a sanitized Windows install-and-scan transcript.
- Linked the quickstart from README and `docs/USAGE.md`.
- Documentation only; no scanner behavior change.
- No cleanup/delete command added.

## v0.1.4

- Expanded path guard coverage for Windows-focused temporary-directory scenarios.
- Added sibling-directory and similar-prefix path tests.
- Added root/self and resolved-child path tests.
- Added POSIX-style relative path output test.
- Added symlink-to-sibling coverage with platform skip.
- Kept scan behavior unchanged.

## v0.1.3

- Added a largest-artifacts section to `findings.md`.
- Added tests for largest-artifact ordering.
- Added JSON report schema contract tests.
- Kept scan behavior unchanged.
- Kept v0.1.x read-only scope unchanged.

## v0.1.2

- Added synthetic sample scan evidence under `examples/sample-scan/`.
- Added `docs/SAMPLE_SCAN_EVIDENCE.md`.
- Updated README with sample scan links.
- Updated roadmap with the v0.1.2 evidence/backlog scope.
- No scanner behavior change.
- No cleanup/delete command added.

## v0.1.1

- Added GitHub Actions CI for Python 3.11, 3.12, and 3.13 on Windows.
- Added bug report, feature request, and safety review issue templates.
- Added pull request template with safety checklist.
- Fixed package metadata URLs.
- Added `docs/ROADMAP.md`.

## v0.1.0

- Initial read-only scanner.
- Added Git repo discovery.
- Added manifest detection.
- Added repo-local artifact detection.
- Added path guard, symlink guard, secret guard.
- Added risk classification.
- Added JSON and Markdown reports.
- Added tests and Windows bootstrap scripts.
