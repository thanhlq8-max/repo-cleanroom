import json
from pathlib import Path

from repo_cleanroom.cli import main


def _write_inventory(tmp_path: Path) -> Path:
    inventory = {
        "docker_inventory_schema_version": "0.6.0",
        "generated_at_utc": "2026-07-05T00:00:00+00:00",
        "mode": "DOCKER_READ_ONLY_SCAN",
        "root": str(tmp_path / "workspace"),
        "containers": [
            {
                "id": "aaa111",
                "name": "demo-web-1",
                "image": "demo-web",
                "state": "exited",
                "status": "Exited (0) 2 days ago",
                "compose_project": "demo",
                "compose_working_dir": str(tmp_path / "workspace" / "demo"),
                "linked_to_workspace": True,
            },
            {
                "id": "bbb222",
                "name": "db",
                "image": "postgres",
                "state": "running",
                "status": "Up 3 hours",
                "compose_project": None,
                "compose_working_dir": None,
                "linked_to_workspace": False,
            },
        ],
        "images": [
            {"id": "img1", "repository": "demo-web", "tag": "latest", "size": "120MB", "dangling": False},
            {"id": "img2", "repository": "<none>", "tag": "<none>", "size": "80MB", "dangling": True},
        ],
        "volumes": [
            {
                "name": "demo_data",
                "driver": "local",
                "compose_project": "demo",
                "linked_to_workspace": True,
            }
        ],
        "summary": {},
        "safety": {"docker_mutation_performed": False},
    }
    path = tmp_path / "docker_inventory.json"
    path.write_text(json.dumps(inventory), encoding="utf-8")
    return path


def _run_plan(tmp_path: Path, inventory_path: Path) -> dict:
    out_dir = tmp_path / "out"
    exit_code = main(
        [
            "docker-plan",
            "--docker-inventory",
            str(inventory_path),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert exit_code == 0
    return json.loads((out_dir / "docker_cleanup_plan.json").read_text(encoding="utf-8"))


def test_docker_plan_action_mapping(tmp_path: Path):
    plan = _run_plan(tmp_path, _write_inventory(tmp_path))

    by_id = {entry["id"]: entry for entry in plan["entries"]}
    assert by_id["aaa111"]["proposed_action"] == "REVIEW_REQUIRED"  # stopped + linked
    assert by_id["bbb222"]["proposed_action"] == "NO_ACTION"  # running
    assert by_id["img1"]["proposed_action"] == "NO_ACTION"  # tagged image
    assert by_id["img2"]["proposed_action"] == "REVIEW_REQUIRED"  # dangling image


def test_docker_plan_never_proposes_volume_deletion(tmp_path: Path):
    plan = _run_plan(tmp_path, _write_inventory(tmp_path))

    volumes = [entry for entry in plan["entries"] if entry["object_type"] == "volume"]
    assert volumes, "plan must include volume entries so review is complete"
    assert all(entry["proposed_action"] == "FORBIDDEN_DEFAULT" for entry in volumes)
    assert plan["summary"]["volumes_proposed_for_deletion"] == 0


def test_docker_plan_is_informational_only(tmp_path: Path):
    plan = _run_plan(tmp_path, _write_inventory(tmp_path))

    assert plan["mode"] == "DOCKER_PLAN_INFORMATIONAL_ONLY"
    assert plan["safety"]["docker_mutation_performed"] is False
    assert plan["safety"]["tool_can_execute_this_plan"] is False
    assert plan["plan_hash"] is None
    assert len(plan["source_docker_inventory"]["sha256"]) == 64


def test_docker_plan_rejects_malformed_inventory(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "an inventory"}', encoding="utf-8")

    exit_code = main(
        ["docker-plan", "--docker-inventory", str(bad), "--out-dir", str(tmp_path / "out")]
    )

    assert exit_code == 2
    assert not (tmp_path / "out" / "docker_cleanup_plan.json").exists()


def test_docker_plan_requires_inventory_argument(tmp_path: Path):
    try:
        main(["docker-plan", "--out-dir", str(tmp_path / "out")])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for missing required --docker-inventory")
