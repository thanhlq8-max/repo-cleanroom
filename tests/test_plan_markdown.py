from repo_cleanroom.planners.plan_markdown import render_plan_markdown


def _plan_fixture() -> dict:
    return {
        "plan_id": "00000000-0000-0000-0000-000000000000",
        "root": "C:/demo/workspace",
        "source_artifact_inventory": {"path": "C:/demo/inventory.json"},
        "entries": [
            {
                "entry_id": "app/node_modules",
                "artifact_type": "node_dependencies",
                "risk": "SAFE",
                "size_bytes": 2000,
                "proposed_action": "PROPOSE_REMOVE",
                "reason": "SAFE repo-local generated artifact; candidate for future approved clean",
            },
            {
                "entry_id": "app/__pycache__",
                "artifact_type": "python_cache",
                "risk": "SAFE",
                "size_bytes": 10,
                "proposed_action": "PROPOSE_REMOVE",
                "reason": "SAFE repo-local generated artifact; candidate for future approved clean",
            },
            {
                "entry_id": "app/.env",
                "artifact_type": "protected_config",
                "risk": "BLOCKED",
                "size_bytes": 37,
                "proposed_action": "FORBIDDEN",
                "reason": "protected sensitive path/name pattern; must never be removed or printed",
            },
        ],
        "summary": {
            "total_entries": 3,
            "proposed_remove_count": 2,
            "proposed_remove_bytes": 2010,
            "review_required_count": 0,
            "blocked_count": 1,
            "no_action_count": 0,
        },
    }


def test_plan_markdown_groups_actions_in_fixed_order():
    report = render_plan_markdown(_plan_fixture())

    proposed = report.index("## Proposed for future approved removal (2 entry(ies), 2.0 KB)")
    forbidden = report.index("## Forbidden (protected items) (1 entry(ies), 37 B)")
    assert proposed < forbidden
    assert "## Requires manual review" not in report
    assert "## No action" not in report


def test_plan_markdown_sorts_by_size_within_group():
    report = render_plan_markdown(_plan_fixture())

    proposed_section = report.split("## Proposed for future approved removal", 1)[1].split(
        "## Forbidden", 1
    )[0]
    assert proposed_section.index("app/node_modules") < proposed_section.index("app/__pycache__")


def test_plan_markdown_states_nothing_was_deleted():
    report = render_plan_markdown(_plan_fixture())

    assert "STATUS: PLAN_ONLY" in report
    assert "Nothing was deleted." in report
    assert "Files removed by this plan: NONE" in report
    assert "A plan is not permission." in report
