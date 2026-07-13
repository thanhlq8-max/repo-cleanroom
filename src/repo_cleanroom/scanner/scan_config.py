"""Optional user scan configuration.

A config file lets the operator (a) exclude paths from detection via glob patterns
and (b) declare extra artifact names to detect. It can only make the scan detect
*less* (ignore) or flag *more as REVIEW* (extra names are never forced SAFE), so it
cannot widen what the tool would ever propose for removal.

The file is explicit: it is never auto-discovered. Pass it with ``scan --config``.
Format (TOML)::

    # names/paths to exclude (fnmatch-style, matched against the repo-relative
    # POSIX path and the basename)
    ignore = ["vendor", "packages/legacy/*", "**/generated"]

    # extra directory/file names to also detect; classified by the normal risk
    # policy, so unknown names become REVIEW — never auto-SAFE
    extra_artifact_names = [".mycache", "buildout"]

    # optional override for the nested-detection depth cap (default 8)
    max_depth = 12
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

# Extra, user-declared artifact names carry this descriptive type. The risk policy
# does not know it, so classify_path returns REVIEW — a deliberate safety default.
CUSTOM_ARTIFACT_TYPE = "custom_configured"


class ScanConfigError(ValueError):
    """Raised when a scan config file is missing or malformed."""


@dataclass(frozen=True)
class ScanConfig:
    """Resolved scan configuration. Empty by default (no config supplied)."""

    ignore: tuple[str, ...] = ()
    extra_artifact_names: tuple[str, ...] = ()
    max_depth: int | None = None

    def is_ignored(self, relative_posix: str, name: str) -> bool:
        """Return True when a candidate should be excluded from detection."""

        for pattern in self.ignore:
            if fnmatch(relative_posix, pattern) or fnmatch(name, pattern):
                return True
        return False

    def as_summary(self) -> dict[str, object]:
        """Serializable summary recorded in scan output for provenance."""

        return {
            "ignore": list(self.ignore),
            "extra_artifact_names": list(self.extra_artifact_names),
            "max_depth": self.max_depth,
        }


EMPTY_CONFIG = ScanConfig()


def _require_str_list(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ScanConfigError(f"config field {key!r} must be a list of strings")
    return tuple(value)


def _require_positive_int(value: object, key: str) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int; reject it explicitly.
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ScanConfigError(f"config field {key!r} must be an integer >= 1")
    return value


def load_scan_config(path: str | Path) -> ScanConfig:
    """Load and validate a scan config TOML file."""

    config_path = Path(path).expanduser()
    if not config_path.is_file():
        raise ScanConfigError(f"config file not found: {config_path}")

    try:
        # utf-8-sig tolerates a BOM, which Windows editors (Notepad, PowerShell
        # Out-File) commonly prepend; a plain utf-8 read would choke on it.
        data = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ScanConfigError(f"config file is not valid TOML: {exc}") from exc

    unknown = set(data) - {"ignore", "extra_artifact_names", "max_depth"}
    if unknown:
        raise ScanConfigError(f"unknown config keys: {sorted(unknown)}")

    ignore = _require_str_list(data.get("ignore", []), "ignore")
    extra = _require_str_list(data.get("extra_artifact_names", []), "extra_artifact_names")
    max_depth = _require_positive_int(data.get("max_depth"), "max_depth")
    return ScanConfig(ignore=ignore, extra_artifact_names=extra, max_depth=max_depth)
