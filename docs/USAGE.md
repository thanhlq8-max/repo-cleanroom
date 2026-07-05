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

## Approve + clean (v0.3.x — approval-gated, SAFE plan entries only)

Review `cleanup_plan.md` first. Approval binds to the exact plan bytes; `clean`
refuses anything except the approved plan on the approved root. There is no
rollback; always run `--dry-run` first.

```powershell
repo-cleanroom approve --plan .cleanroom\cleanup_plan.json --approved-by "your-name" --out-dir .cleanroom
repo-cleanroom clean --root F:\GitHub --plan .cleanroom\cleanup_plan.json --token .cleanroom\approval_token.json --yes-exact-plan <PLAN_HASH> --dry-run --out-dir .cleanroom
repo-cleanroom clean --root F:\GitHub --plan .cleanroom\cleanup_plan.json --token .cleanroom\approval_token.json --yes-exact-plan <PLAN_HASH> --out-dir .cleanroom
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
