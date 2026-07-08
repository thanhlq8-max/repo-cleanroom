# Security Policy

## Supported status

Repo Cleanroom v1.1.x is the supported stable line. All commands are read-only or report-only except `clean`, which removes only SAFE entries of one byte-exact, human-approved plan and re-checks every guard at delete time. Security fixes land on `main` and are released from there; older pre-1.0 milestones are not maintained.

## Sensitive data policy

Do not include secrets in issues, logs, screenshots, or reports.

Sensitive examples:

- API keys and tokens
- passwords
- private keys
- seed or mnemonic phrases
- `.env` content
- SSH/GPG material
- wallet files
- cloud credentials
- cookies/session data

## Reporting a vulnerability

Open a private security advisory on GitHub if available. If private reporting is unavailable, open a minimal public issue that does not include secret values, exploit payloads, or sensitive paths.

## Safety guarantees not made

Repo Cleanroom does not claim to fully clean every repository or repair a machine. Removal is limited to approved SAFE plan entries, there is no rollback, and attestation reports only what the logs prove.
