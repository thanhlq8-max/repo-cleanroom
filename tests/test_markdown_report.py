from repo_cleanroom.reports.markdown_report import render_findings_markdown


def test_findings_report_includes_largest_artifacts_sorted():
    inventory = {
        "root": "C:/demo/workspace",
        "repos": [
            {"name": "small", "relative_path": "small", "path": "C:/demo/workspace/small"},
            {"name": "large", "relative_path": "large", "path": "C:/demo/workspace/large"},
        ],
        "manifests": [],
    }
    artifact_inventory = {
        "artifacts": [
            {
                "risk": "SAFE",
                "artifact_type": "python_cache",
                "size_bytes": 10,
                "repo_relative_path": "small",
                "relative_path": ".pytest_cache",
                "reason": "common repo-local generated artifact",
            },
            {
                "risk": "SAFE",
                "artifact_type": "node_dependencies",
                "size_bytes": 2000,
                "repo_relative_path": "large",
                "relative_path": "node_modules",
                "reason": "common repo-local generated artifact",
            },
            {
                "risk": "REVIEW",
                "artifact_type": "runtime_logs",
                "size_bytes": 100,
                "repo_relative_path": "large",
                "relative_path": "logs",
                "reason": "may contain user/runtime data; requires review",
            },
        ]
    }

    report = render_findings_markdown(inventory, artifact_inventory)

    assert "## Largest artifacts" in report
    largest_section = report.split("## Largest artifacts", 1)[1].split("## Repositories", 1)[0]
    first = largest_section.index("large/node_modules")
    second = largest_section.index("large/logs")
    third = largest_section.index("small/.pytest_cache")
    assert first < second < third


def test_findings_report_largest_artifacts_empty_state():
    inventory = {"root": "C:/demo/workspace", "repos": [], "manifests": []}
    artifact_inventory = {"artifacts": []}

    report = render_findings_markdown(inventory, artifact_inventory)

    largest_section = report.split("## Largest artifacts", 1)[1].split("## Repositories", 1)[0]
    assert "No known repo-local artifacts were detected." in largest_section
