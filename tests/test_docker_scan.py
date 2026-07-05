import json
from pathlib import Path

import pytest

import repo_cleanroom.dockerscan.docker_scan as docker_scan_module
from repo_cleanroom.cli import main
from repo_cleanroom.dockerscan.docker_scan import (
    ALLOWED_QUERIES,
    DockerScanError,
    build_docker_inventory,
    run_query,
)

_MUTATING_VERBS = {
    "rm", "rmi", "prune", "kill", "stop", "start", "restart", "pause", "unpause",
    "run", "create", "exec", "build", "push", "pull", "commit", "update", "rename",
}


def _fake_runner_factory(root: Path):
    working_dir = str(root / "demo")

    outputs = {
        "version": '{"Client":{"Version":"27.0.0"}}\n',
        "containers": (
            json.dumps(
                {
                    "ID": "aaa111",
                    "Names": "demo-web-1",
                    "Image": "demo-web",
                    "State": "exited",
                    "Status": "Exited (0) 2 days ago",
                    "Labels": (
                        "com.docker.compose.project=demo,"
                        f"com.docker.compose.project.working_dir={working_dir}"
                    ),
                }
            )
            + "\n"
            + json.dumps(
                {
                    "ID": "bbb222",
                    "Names": "unrelated",
                    "Image": "postgres",
                    "State": "running",
                    "Status": "Up 3 hours",
                    "Labels": "",
                }
            )
            + "\n"
        ),
        "images": (
            json.dumps({"ID": "img1", "Repository": "demo-web", "Tag": "latest", "Size": "120MB"})
            + "\n"
            + json.dumps({"ID": "img2", "Repository": "<none>", "Tag": "<none>", "Size": "80MB"})
            + "\n"
        ),
        "volumes": (
            json.dumps(
                {
                    "Name": "demo_data",
                    "Driver": "local",
                    "Labels": (
                        "com.docker.compose.project=demo,"
                        f"com.docker.compose.project.working_dir={working_dir}"
                    ),
                }
            )
            + "\n"
        ),
    }

    def runner(argv: list[str]) -> str:
        for name, allowed in ALLOWED_QUERIES.items():
            if argv == allowed:
                return outputs[name]
        raise AssertionError(f"unexpected docker argv: {argv}")

    return runner


def test_whitelist_contains_only_read_verbs():
    for argv in ALLOWED_QUERIES.values():
        assert not _MUTATING_VERBS.intersection(argv), f"mutating verb in whitelist: {argv}"


def test_run_query_refuses_anything_outside_whitelist():
    with pytest.raises(DockerScanError):
        run_query("system prune", lambda argv: "")


def test_inventory_links_compose_objects_to_workspace(tmp_path: Path):
    root = tmp_path / "workspace"
    (root / "demo").mkdir(parents=True)

    payload = build_docker_inventory(root, runner=_fake_runner_factory(root))

    assert payload["mode"] == "DOCKER_READ_ONLY_SCAN"
    by_name = {c["name"]: c for c in payload["containers"]}
    assert by_name["demo-web-1"]["linked_to_workspace"] is True
    assert by_name["demo-web-1"]["compose_project"] == "demo"
    assert by_name["unrelated"]["linked_to_workspace"] is False

    assert payload["summary"]["containers_linked_to_workspace"] == 1
    assert payload["summary"]["dangling_images"] == 1
    assert payload["volumes"][0]["linked_to_workspace"] is True
    assert payload["safety"]["docker_mutation_performed"] is False


def test_cli_docker_scan_writes_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "workspace"
    (root / "demo").mkdir(parents=True)
    monkeypatch.setattr(docker_scan_module, "default_runner", _fake_runner_factory(root))

    out_dir = tmp_path / "out"
    exit_code = main(["docker-scan", "--root", str(root), "--out-dir", str(out_dir)])

    assert exit_code == 0
    payload = json.loads((out_dir / "docker_inventory.json").read_text(encoding="utf-8"))
    assert payload["summary"]["containers"] == 2


def test_cli_docker_scan_fails_cleanly_without_docker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "workspace"
    root.mkdir()

    def unavailable(argv: list[str]) -> str:
        raise FileNotFoundError("docker not installed")

    monkeypatch.setattr(docker_scan_module, "default_runner", unavailable)

    out_dir = tmp_path / "out"
    exit_code = main(["docker-scan", "--root", str(root), "--out-dir", str(out_dir)])

    assert exit_code == 2
    assert not (out_dir / "docker_inventory.json").exists()


def test_docker_scan_requires_root(tmp_path: Path):
    try:
        main(["docker-scan", "--out-dir", str(tmp_path / "out")])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for missing required --root")
