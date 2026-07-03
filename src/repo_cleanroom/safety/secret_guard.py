"""Path/name-based protection for sensitive files.

v0.1.0 does not read secret file contents. It only classifies path names.
"""

from __future__ import annotations

from pathlib import Path


EXACT_PROTECTED_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials.json",
    "credentials.yaml",
    "credentials.yml",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "known_hosts",
}

PROTECTED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".crt",
    ".cer",
    ".kdbx",
}

PROTECTED_SUBSTRINGS = {
    "mnemonic",
    "seedphrase",
    "seed_phrase",
    "private_key",
    "wallet",
    "token",
    "secret",
}


def is_protected_path(path: str | Path) -> bool:
    """Return True when a path name indicates sensitive material."""

    p = Path(path)
    name = p.name.lower()
    stem = p.stem.lower()
    suffix = p.suffix.lower()

    if name in EXACT_PROTECTED_NAMES:
        return True
    if suffix in PROTECTED_SUFFIXES:
        return True
    if any(part in name or part in stem for part in PROTECTED_SUBSTRINGS):
        return True
    return False


def protected_reason(path: str | Path) -> str | None:
    """Return a public-safe reason for protected classification."""

    if not is_protected_path(path):
        return None
    return "protected sensitive path/name pattern"
