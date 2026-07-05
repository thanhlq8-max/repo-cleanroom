"""Generate a synthetic demo workspace for trying the scan/plan pipeline.

The generated tree contains fake Git repositories with the common artifact
shapes the scanner detects (node_modules, .venv, __pycache__, dist, target,
logs) plus a placeholder .env so the BLOCKED path is demonstrated. All content
is synthetic; the .env value is an obvious placeholder, never a real secret.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEMO_SCHEMA_VERSION = "0.7.0"

_PLACEHOLDER_ENV = "PLACEHOLDER=synthetic-demo-value\n"


class DemoWorkspaceError(ValueError):
    """Raised when the demo workspace cannot be generated safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo_web(repo: Path) -> None:
    (repo / ".git").mkdir(parents=True)
    _write(repo / "package.json", '{"name": "demo-web-app", "version": "1.0.0"}\n')
    _write(repo / "node_modules" / "left-pad" / "index.js", "module.exports = {};\n")
    _write(repo / "node_modules" / "left-pad" / "package.json", '{"name": "left-pad"}\n')
    _write(repo / "dist" / "bundle.js", "console.log('synthetic demo bundle');\n")
    _write(repo / ".env", _PLACEHOLDER_ENV)


def _make_repo_python(repo: Path) -> None:
    (repo / ".git").mkdir(parents=True)
    _write(repo / "pyproject.toml", '[project]\nname = "demo-py-tool"\nversion = "0.0.1"\n')
    _write(repo / ".venv" / "Lib" / "site.py", "# synthetic virtualenv file\n")
    _write(repo / "__pycache__" / "demo.cpython-313.pyc", "synthetic\n")
    _write(repo / ".pytest_cache" / "CACHEDIR.TAG", "Signature: 8a477f597d28d172789f06886806bc55\n")
    _write(repo / "logs" / "run.log", "2026-01-01 synthetic demo log line\n")


def _make_repo_rust(repo: Path) -> None:
    (repo / ".git").mkdir(parents=True)
    _write(repo / "Cargo.toml", '[package]\nname = "demo-rust-cli"\nversion = "0.1.0"\n')
    _write(repo / "target" / "debug" / "demo-rust-cli.d", "synthetic build metadata\n")


def generate_demo_workspace(out_dir: str | Path, repo_count: int = 3) -> dict[str, Any]:
    """Create the synthetic workspace. Refuses existing non-empty targets.

    repo_count above 3 repeats the python repo shape with numbered names,
    which is what the benchmark uses to scale the workspace.
    """

    if repo_count < 1:
        raise DemoWorkspaceError("repo count must be at least 1")

    target = Path(out_dir).expanduser()
    if target.exists():
        if not target.is_dir():
            raise DemoWorkspaceError(f"target exists and is not a directory: {target}")
        if any(target.iterdir()):
            raise DemoWorkspaceError(
                f"target directory is not empty: {target}; refusing to write into existing data"
            )
    target.mkdir(parents=True, exist_ok=True)

    builders = [
        ("demo-web-app", _make_repo_web),
        ("demo-py-tool", _make_repo_python),
        ("demo-rust-cli", _make_repo_rust),
    ]
    created: list[str] = []
    for index in range(repo_count):
        if index < len(builders):
            name, builder = builders[index]
        else:
            name, builder = f"demo-py-tool-{index:04d}", _make_repo_python
        builder(target / name)
        created.append(name)

    return {
        "demo_schema_version": DEMO_SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "mode": "SYNTHETIC_DEMO_WORKSPACE",
        "root": str(target.resolve()),
        "repos_created": created,
        "synthetic_only": True,
    }
