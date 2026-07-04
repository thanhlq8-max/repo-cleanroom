# Windows quickstart transcript

This transcript shows a minimal successful Windows run with sanitized paths.
The `C:\cleanroom-demo` paths are placeholders, not a real user profile, and
the target workspace is a disposable synthetic repo.

Repo Cleanroom v0.1.x is read-only. The scan below writes reports only; it does
not delete files, uninstall packages, prune Docker, modify Git state, read shell
history, or change system configuration.

For stable sample output that can be reviewed without running the CLI, see
[`examples/sample-scan/`](../examples/sample-scan/) and
[`docs/SAMPLE_SCAN_EVIDENCE.md`](SAMPLE_SCAN_EVIDENCE.md).

## Install and validate

```powershell
PS C:\cleanroom-demo> git clone https://github.com/thanhlq8-max/repo-cleanroom.git
PS C:\cleanroom-demo> cd repo-cleanroom
PS C:\cleanroom-demo\repo-cleanroom> py -m venv .venv
PS C:\cleanroom-demo\repo-cleanroom> .\.venv\Scripts\Activate.ps1
(.venv) PS C:\cleanroom-demo\repo-cleanroom> py -m pip install -e .[dev]
Successfully installed build pytest repo-cleanroom
(.venv) PS C:\cleanroom-demo\repo-cleanroom> py -m pytest -q
.s..........                                                             [100%]
```

## Create a disposable workspace

```powershell
(.venv) PS C:\cleanroom-demo\repo-cleanroom> mkdir C:\cleanroom-demo\workspace\demo\.git
(.venv) PS C:\cleanroom-demo\repo-cleanroom> mkdir C:\cleanroom-demo\workspace\demo\node_modules
(.venv) PS C:\cleanroom-demo\repo-cleanroom> '{}' | Set-Content C:\cleanroom-demo\workspace\demo\package.json
(.venv) PS C:\cleanroom-demo\repo-cleanroom> 'x' | Set-Content C:\cleanroom-demo\workspace\demo\node_modules\left-pad.txt
```

## Run the read-only scan

```powershell
(.venv) PS C:\cleanroom-demo\repo-cleanroom> repo-cleanroom scan --root C:\cleanroom-demo\workspace --out-dir .cleanroom
STATUS: READ_ONLY_SCAN_COMPLETE
ROOT: C:\cleanroom-demo\workspace
OUT_DIR: C:\cleanroom-demo\repo-cleanroom\.cleanroom
REPOS_SCANNED: 1
ARTIFACTS_FOUND: 1
ESTIMATED_ARTIFACT_BYTES: 3
CLEANUP_PERFORMED: NO
```

The generated report files are:

```text
.cleanroom\schema_version.json
.cleanroom\inventory.json
.cleanroom\artifact_inventory.json
.cleanroom\findings.md
.cleanroom\public_safety_check.json
```

Open `.cleanroom\findings.md` to review the Markdown summary. The transcript
demonstrates the v0.1.x contract: scan, report, review, and no cleanup.
