"""Evidence line sanitization.

Implements docs/COMMAND_EVIDENCE_PRIVACY.md section 3, in order. Over-redaction is
acceptable; under-redaction is a bug (pattern B-008).
"""

from __future__ import annotations

import re

from repo_cleanroom.safety.secret_guard import is_protected_path

REDACTED = "[REDACTED]"

REDACTED_ARGS = "[REDACTED-ARGS]"

# Rule 1: credential-bearing URL userinfo.
_URL_USERINFO = re.compile(r"(\w+://)[^\s/@:]+:[^\s/@]+@")

# Rule 2a: sensitive command-line flags (--password value, --token=value, -p=value forms).
_SENSITIVE_FLAG = re.compile(
    r"(?i)(--?[\w-]*(?:password|passwd|pwd|token|secret|auth|credential|bearer|apikey|api-key)[\w-]*)([= ])(\S+)"
)

# Rule 2b: sensitive assignments (TOKEN=..., my_secret=...).
_SENSITIVE_ASSIGN = re.compile(
    r"(?i)\b([\w-]*(?:password|passwd|pwd|token|secret|auth|credential|bearer|apikey|api_key)[\w-]*)=(\S+)"
)

# Rule 3: token-shaped opaque strings — 20+ [A-Za-z0-9_-] chars including a digit.
_TOKEN_SHAPE = re.compile(r"\b(?=[A-Za-z0-9_\-]*\d)[A-Za-z0-9_\-]{20,}\b")


def sanitize_line(line: str) -> str:
    """Sanitize one evidence line for persistence."""

    sanitized = _URL_USERINFO.sub(rf"\g<1>{REDACTED}@", line)
    sanitized = _SENSITIVE_FLAG.sub(rf"\g<1>\g<2>{REDACTED}", sanitized)
    sanitized = _SENSITIVE_ASSIGN.sub(rf"\g<1>={REDACTED}", sanitized)
    sanitized = _TOKEN_SHAPE.sub(REDACTED, sanitized)

    # Rule 4: if any argument still looks like a protected filename, keep only the
    # command word.
    parts = sanitized.split()
    if len(parts) > 1 and any(is_protected_path(part) for part in parts[1:]):
        return f"{parts[0]} {REDACTED_ARGS}"
    return sanitized
