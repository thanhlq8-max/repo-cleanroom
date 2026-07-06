# Threat Model

Status: v0.9.1 safety audit. This document describes what Repo Cleanroom defends
against, how each defense is implemented, and which risks remain.

## Adversary model

The primary adversary is **the content of a scanned repository**. A repository is
untrusted input: it may be cloned from anywhere and may contain names, links, and
structures crafted to abuse a cleanup tool. The tool must remain safe even when the
workspace contains:

1. symlinks or Windows junctions pointing outside the scan root;
2. hostile file names (unicode tricks, shell metacharacters, template-like strings);
3. secret-looking files whose content must never be read into any output;
4. structures that change between plan approval and clean execution (TOCTOU).

A secondary concern is operator error: approving the wrong plan, running clean on the
wrong root, or reusing an old token. Those are addressed by the approval design
(`docs/APPROVAL_TOKEN.md`), not repeated here.

## Threats and mitigations

| # | Threat | Mitigation | Enforced in | Tested by |
|---|---|---|---|---|
| T1 | Symlink inside an artifact redirects size estimation or deletion outside the root | Link-like paths are never traversed; symlinks inside an entry are unlinked as links, never followed | `safety/symlink_guard.py`, `scanner/size_indexer.py`, `cleaner/executor.py` | `test_repo_scan.py`, `test_clean_command.py`, `test_safety_audit.py` |
| T2 | **Windows junction** inside an artifact — `Path.is_symlink()` is False for junctions and `os.walk(followlinks=False)` descends into them, so a junction planted in a SAFE entry could redirect deletion outside the root | Every boundary decision uses `is_link_like()` (symlink **or** NTFS reparse point via `lstat` `FILE_ATTRIBUTE_REPARSE_POINT`); scan reports junction artifacts as link-like with size 0; clean refuses any entry containing a non-symlink reparse point (`SKIPPED_GUARD_FAIL`, nothing removed) | `safety/symlink_guard.py` (`is_reparse_point`, `is_link_like`), `scanner/size_indexer.py`, `cleaner/executor.py` | `test_safety_audit.py` (junction escape, junction artifact, planted junction, entry-became-junction) |
| T3 | Entry replaced by a symlink/junction between approve and clean | Delete-time guard re-checks `is_link_like` on every entry; changed entries → `SKIPPED_CHANGED` | `cleaner/executor.py` `_guard_entry` | `test_clean_command.py`, `test_safety_audit.py` |
| T4 | Path escape via plan tampering | Approval token binds to the exact plan bytes (SHA-256); any mutation invalidates it; every entry re-validated against the root at delete time | `cleaner/approval.py`, `safety/path_guard.py` | `test_clean_command.py` |
| T5 | Secret content leaking into reports | Secrets are classified by path/name only; no code path reads secret file content into an output; evidence input is sanitized before persisting | `safety/secret_guard.py`, `evidence/sanitizer.py` | `test_secret_guard.py`, `test_evidence_command.py`, `test_safety_audit.py` (content-marker sweep) |
| T6 | Secret planted inside a SAFE entry after approval | Delete-time tree inspection refuses entries containing protected names (`SKIPPED_PROTECTED`) | `cleaner/executor.py` `_inspect_entry_tree` | `test_clean_command.py` |
| T7 | Hostile file names breaking the scan or injecting into reports | Names are treated as data everywhere; HTML report escapes every workspace value; scan tolerates unicode/metacharacter names | `reports/html_report.py`, scan pipeline | `test_html_report.py` (XSS payloads), `test_safety_audit.py` (hostile names) |
| T8 | Script execution from the scanned repository | No code path executes workspace content; Docker queries use a fixed read-only argv whitelist with `shell=False` | whole codebase, `dockerscan/docker_scan.py` | `test_docker_scan.py` (whitelist has no mutating verb) |
| T9 | Deletion crossing a filesystem/mount boundary | Delete-time inspection compares `st_dev` and refuses entries crossing devices | `cleaner/executor.py` | `test_clean_recovery.py` |
| T10 | Shell history exfiltration | No code path locates or reads shell history; evidence enters only via explicit `--evidence-file` | `docs/COMMAND_EVIDENCE_PRIVACY.md`, `evidence/importer.py` | `test_evidence_command.py` |

## Audit finding (v0.9.1): junction traversal

The v0.9.1 audit empirically confirmed T2 on every supported Python version
(3.11–3.13): junctions were reported `is_symlink=False` and both size estimation and
bottom-up removal walked through them. A same-volume junction also defeats the
`st_dev` mount check (T9), because both sides share the volume device id.

Fix shipped with this audit:

- `is_reparse_point()` / `is_link_like()` in `safety/symlink_guard.py` — detects any
  NTFS reparse point via `lstat`, works on Python 3.11+ and returns False on POSIX;
- scan: junction artifacts are reported link-like, size 0, never traversed;
- clean: entries containing a non-symlink reparse point are refused entirely
  (fail-safe: `SKIPPED_GUARD_FAIL`, nothing in that entry is removed); the removal
  walk itself prunes link-like directories and aborts on unexpected reparse points.

## Residual risks

- **TOCTOU window**: guards re-run at delete time, but a filesystem race in the
  microseconds between the final check and the `unlink`/`rmdir` call is not
  preventable from user-mode Python. The exposure is bounded to paths already
  validated inside the root.
- **Hard links**: removing a hard-linked file inside an artifact removes one directory
  entry; other links keep the content. No escape (the unlink is scoped to the entry),
  but disk space may not be reclaimed.
- **Exotic reparse tags** (OneDrive placeholders, dedup points): treated identically
  to junctions — the entry is refused rather than interpreted. This can produce
  false-positive skips; that is the intended fail-safe direction.
- **Long paths** (> 260 chars without the Windows long-path opt-in): removal may fail
  with `OSError`; the executor records `ERROR` and fail-fasts without partial silent
  loss.

Reports of new attack vectors follow the process in `SECURITY.md`.
