# Scan configuration

`scan` accepts an optional TOML config file via `--config`. It is never
auto-discovered — you always pass it explicitly, in keeping with the tool's
no-hidden-defaults policy.

```powershell
repo-cleanroom scan --root F:\GitHub --out-dir .cleanroom --config cleanroom.toml
```

## Format

```toml
# Paths/names to exclude from detection. fnmatch-style patterns, matched against
# both the repo-relative POSIX path and the basename.
ignore = [
  "vendor",              # any directory named "vendor", at any depth
  "packages/legacy/*",   # everything under packages/legacy
  "**/generated",        # any path ending in /generated
]

# Extra directory/file names to also detect, beyond the built-in set.
extra_artifact_names = [".mycache", "buildout"]

# Optional override for how deep nested detection walks (repo-relative). Default 8.
# Raise it for very deep monorepos; lower it to bound scan cost on huge trees.
max_depth = 12
```

Only these three keys are allowed; unknown keys are rejected.

## Semantics

- **`ignore`** — a matched directory is pruned (not recorded, not descended into);
  a matched file is skipped. Matching is `fnmatch`-style against the candidate's
  repo-relative POSIX path *and* its basename, so `vendor` excludes every `vendor`
  directory while `packages/legacy/*` targets one subtree.
- **`extra_artifact_names`** — additional names detected alongside the built-ins.
  They are classified by the normal risk policy, so a name the policy does not know
  becomes **REVIEW** — never auto-`SAFE`. Config can therefore only make the scan
  detect *less* (ignore) or flag *more as REVIEW* (extra names); it can never widen
  what the tool would propose for removal.
- **`max_depth`** — overrides the nested-detection depth cap (repo-relative,
  default 8). Must be an integer ≥ 1. Detected artifacts already prune the walk, so
  the default suits most repos; raise it for unusually deep monorepos or lower it to
  bound cost on very large trees.

## Provenance

The applied config is recorded in `inventory.json` and `artifact_inventory.json`
under `scan_config` (`{ "ignore": [...], "extra_artifact_names": [...], "max_depth":
null }`), so a plan built from that inventory carries an auditable record of what was
excluded. Running `scan` without `--config` records an empty `scan_config`
(`max_depth: null` meaning the built-in default).

## Safety note

Ignoring a path means it will not be reported — including as `BLOCKED`. Since `clean`
only ever acts on entries of an approved plan, an ignored path simply never enters a
plan and is never removed. Ignore is an explicit operator choice and only ever
narrows the scan.
