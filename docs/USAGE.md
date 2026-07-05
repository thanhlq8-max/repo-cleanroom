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

## Verify + attest (v0.4.x — read-only evidence)

`verify` compares the filesystem against the plan and action log (removed entries must
be gone, everything else must still exist). `attest` assembles the final evidence pack.

```powershell
repo-cleanroom verify --root F:\GitHub --plan .cleanroom\cleanup_plan.json --action-log .cleanroom\clean_action_log.json --out-dir .cleanroom
repo-cleanroom attest --plan .cleanroom\cleanup_plan.json --action-log .cleanroom\clean_action_log.json --verify .cleanroom\verify.json --out-dir .cleanroom
```

Outputs: `verify.json`, then `attestation.json` + `final_report.md` (cleaned / skipped /
failed / blocked / unchanged). A failed verification is attested as a discrepancy.

## Evidence mapping (v0.5.x — explicit opt-in, informational)

Assemble a plain-text file of commands you remember running, then map it to detected
artifacts. The tool never reads shell history and never executes evidence lines; all
output is sanitized per [`COMMAND_EVIDENCE_PRIVACY.md`](COMMAND_EVIDENCE_PRIVACY.md).

```powershell
repo-cleanroom evidence --evidence-file my_commands.txt --scan-artifacts .cleanroom\artifact_inventory.json --out-dir .cleanroom
```

## Docker scan (v0.6.x — read-only, explicit opt-in)

Queries Docker through a fixed whitelist of read-only CLI commands and relates
compose-labeled objects to your workspace. Nothing is created, stopped, or removed.

```powershell
repo-cleanroom docker-scan --root F:\GitHub --out-dir .cleanroom

repo-cleanroom docker-plan --docker-inventory .cleanroom\docker_inventory.json --out-dir .cleanroom
```

`docker-plan` is informational only: it suggests what you may review manually
(stopped workspace containers, dangling images), never proposes volume deletion,
and cannot be executed by this tool.

## HTML report (v0.7.x — static review page)

```powershell
repo-cleanroom html-report --inventory .cleanroom\inventory.json --scan-artifacts .cleanroom\artifact_inventory.json --out-dir .cleanroom
```

Produces a self-contained `findings.html` (no scripts, no external resources).

## Demo workspace (v0.7.x — synthetic try-it fixture)

```powershell
repo-cleanroom demo-workspace --out-dir C:\cleanroom-demo\workspace
repo-cleanroom scan --root C:\cleanroom-demo\workspace --out-dir C:\cleanroom-demo\.cleanroom
```

The generator refuses non-empty target directories and writes only synthetic
placeholder content.

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
