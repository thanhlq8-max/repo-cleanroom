# Security Policy

## Supported status

Repo Cleanroom is pre-1.0 alpha. v0.1.0 is read-only and has no cleanup/delete command.

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

Repo Cleanroom does not claim to fully clean every repository or repair a machine. v0.1.0 only reports findings.
