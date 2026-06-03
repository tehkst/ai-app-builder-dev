import json

from app.platform.workspaces.db_registry import db_workspace_registry
from app.platform.workspaces.schemas import (
    WorkspaceRegistryCreate,
    WorkspaceStatus,
)


TENANT_ID = "db-registry-test-tenant"
WORKSPACE_ID = "db-registry-test-workspace"
PROJECT_ID = "db-registry-test-project"


def validate_db_workspace_registry() -> dict:
    created = db_workspace_registry.create_workspace(
        WorkspaceRegistryCreate(
            tenant_id=TENANT_ID,
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            metadata={
                "source": "db_registry_validation",
            },
        )
    )

    generated = db_workspace_registry.increment_generation_count(
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
    )

    repaired = db_workspace_registry.increment_repair_count(
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
    )

    ready = db_workspace_registry.update_workspace_status(
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        status=WorkspaceStatus.READY,
    )

    fetched = db_workspace_registry.get_workspace(
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
    )

    passed = (
        created.project_id == PROJECT_ID
        and generated.generation_count >= 1
        and repaired.repair_count >= 1
        and ready.status == WorkspaceStatus.READY
        and fetched is not None
        and fetched.status == WorkspaceStatus.READY
    )

    return {
        "passed": passed,
        "tenant_id": TENANT_ID,
        "workspace_id": WORKSPACE_ID,
        "project_id": PROJECT_ID,
        "created_status": created.status,
        "generation_count": generated.generation_count,
        "repair_count": repaired.repair_count,
        "ready_status": ready.status,
        "fetched_status": fetched.status if fetched else None,
    }


def main() -> int:
    report = validate_db_workspace_registry()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
