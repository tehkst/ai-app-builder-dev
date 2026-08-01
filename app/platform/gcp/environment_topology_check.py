from __future__ import annotations

from pathlib import Path

from app.platform.architecture_knowledge_graph.environment_topology import ENVIRONMENTS

WORKFLOW = Path(".github/workflows/platform-deploy.yml")


def main() -> None:
    _check_registry_self_consistency()
    _check_workflow_matches_registry()
    print("ENVIRONMENT TOPOLOGY CHECK PASSED")


def _check_registry_self_consistency() -> None:
    # cloud_run_service is a literal GCP resource name - it can never be legitimately
    # shared between two environments, full stop.
    services = [env["cloud_run_service"] for env in ENVIRONMENTS.values()]
    assert len(services) == len(set(services)), "Two environments declare the same cloud_run_service: %s" % services

    # database/secret sharing between non-production environments is an intentional,
    # documented choice (staging and dev are both synthetic sandboxes - see
    # environment_topology.py). Production sharing either with anything else is the
    # exact bug this check exists to prevent from ever landing again.
    production = ENVIRONMENTS["production"]
    for name, env in ENVIRONMENTS.items():
        if name == "production":
            continue
        assert env["cloud_sql_database"] != production["cloud_sql_database"], (
            "%s declares the same cloud_sql_database as production" % name
        )
        assert env["database_secret"] != production["database_secret"], (
            "%s declares the same database_secret as production" % name
        )


def _check_workflow_matches_registry() -> None:
    assert WORKFLOW.exists(), "Missing platform deploy workflow"
    content = WORKFLOW.read_text(encoding="utf-8")
    for env in ENVIRONMENTS.values():
        assert env["database_secret"] in content, (
            "platform-deploy.yml never references declared secret %s" % env["database_secret"]
        )
        # The connection name's project/region are built from ${{ vars.GCP_PROJECT_ID }}/
        # ${{ vars.GCP_REGION }} in the workflow (already asserted present by
        # deploy_check.py) rather than hardcoded, so only the instance name itself needs
        # to appear literally.
        assert env["cloud_sql_instance"] in content, (
            "platform-deploy.yml never references declared Cloud SQL instance %s"
            % env["cloud_sql_instance"]
        )
    assert "--add-cloudsql-instances" in content, "platform-deploy.yml must explicitly attach a Cloud SQL instance"


if __name__ == "__main__":
    main()
