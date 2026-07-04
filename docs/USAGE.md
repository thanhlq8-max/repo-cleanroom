# Usage

A sanitized Windows transcript of the full flow below is available in [`WINDOWS_QUICKSTART.md`](WINDOWS_QUICKSTART.md).

## Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .[dev]
```

## Scan

```powershell
repo-cleanroom scan --root F:\GitHub --out-dir .cleanroom
```

## Plan (PLAN_ONLY — removes nothing)

```powershell
repo-cleanroom plan --scan-artifacts .cleanroom\artifact_inventory.json --out-dir .cleanroom
```

## Read outputs

```powershell
Get-Content .cleanroom\findings.md
Get-Content .cleanroom\artifact_inventory.json
```

## Validate development checkout

```powershell
py -m compileall src tests
py -m pytest -q
py -m build
```
