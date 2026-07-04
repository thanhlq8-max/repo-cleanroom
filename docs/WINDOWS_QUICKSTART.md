# Windows Quickstart

This is a sanitized transcript of a real Repo Cleanroom run on Windows 10 with Python 3.13.

> v0.1.x is **read-only**. The `scan` command writes report files into the directory you select with `--out-dir` and changes nothing else. There is no cleanup, delete, or uninstall behavior in this version.

All private local paths in this transcript were replaced with the placeholder prefix `C:\cleanroom-demo`. The scanned workspace is synthetic demo data, not a real project.

## 1. Install

```powershell
git clone https://github.com/thanhlq8-max/repo-cleanroom.git
cd repo-cleanroom
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .[dev]
```

Check the CLI is available:

```text
PS C:\cleanroom-demo\repo-cleanroom> repo-cleanroom --help
usage: repo-cleanroom [-h] {scan} ...

Read-only scanner for repo-local generated artifacts.

positional arguments:
  {scan}
    scan      scan a user-selected root and write read-only reports

options:
  -h, --help  show this help message and exit
```

## 2. Prepare a disposable demo workspace

You can point `--root` at any workspace you want to audit. For this transcript a synthetic workspace was used:

```text
C:\cleanroom-demo\workspace\
  demo-web-app\        (git repo: package.json, node_modules\, dist\, .env)
  demo-py-tool\        (git repo: pyproject.toml, .venv\, __pycache__\)
```

The `.env` file contains only a placeholder value. Never commit or share real secret files.

## 3. Run a read-only scan

`--root` and `--out-dir` are both required. There are no hidden defaults.

```text
PS C:\cleanroom-demo> repo-cleanroom scan --root C:\cleanroom-demo\workspace --out-dir C:\cleanroom-demo\.cleanroom
STATUS: READ_ONLY_SCAN_COMPLETE
ROOT: C:\cleanroom-demo\workspace
OUT_DIR: C:\cleanroom-demo\.cleanroom
REPOS_SCANNED: 2
ARTIFACTS_FOUND: 5
ESTIMATED_ARTIFACT_BYTES: 127
CLEANUP_PERFORMED: NO
```

## 4. Review the reports

```powershell
Get-Content C:\cleanroom-demo\.cleanroom\findings.md
```

Excerpt from the generated `findings.md`:

```text
# Repo Cleanroom Findings

STATUS: READ_ONLY_SCAN_COMPLETE

## Risk counts

| Risk | Count |
|---|---:|
| SAFE | 4 |
| REVIEW | 0 |
| DANGEROUS | 0 |
| BLOCKED | 1 |

## Largest artifacts

| Risk | Size | Repo-local path | Type |
|---|---:|---|---|
| BLOCKED | 37 B | `demo-web-app/.env` | `protected_config` |
| SAFE | 26 B | `demo-py-tool/.venv` | `python_virtualenv` |
| SAFE | 25 B | `demo-web-app/dist` | `build_output` |
| SAFE | 25 B | `demo-web-app/node_modules` | `node_dependencies` |
| SAFE | 14 B | `demo-py-tool/__pycache__` | `python_cache` |
```

Notes on what the scan did:

- The `.env` file was classified `BLOCKED` from its path/name only. Its content was never read or printed.
- `SAFE` means "candidate for a future user-approved cleanup plan", not "deleted". Nothing was deleted.
- Symlink targets are not traversed during size estimation.

The full output set is:

```text
C:\cleanroom-demo\.cleanroom\schema_version.json
C:\cleanroom-demo\.cleanroom\inventory.json
C:\cleanroom-demo\.cleanroom\artifact_inventory.json
C:\cleanroom-demo\.cleanroom\findings.md
C:\cleanroom-demo\.cleanroom\public_safety_check.json
```

## 5. More sample output

A complete synthetic report set is committed in this repository:

- [`docs/SAMPLE_SCAN_EVIDENCE.md`](SAMPLE_SCAN_EVIDENCE.md)
- [`examples/sample-scan/`](../examples/sample-scan/)
