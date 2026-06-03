import json

from app.platform.persistence.crud import (
    create_project,
    create_tenant,
    create_workspace,
    get_project,
)
from app.platform.persistence.database import (
    PlatformSessionLocal,
    create_platform_tables,
)


DEFAULT_TENANT_ID = "default-tenant"
DEFAULT_WORKSPACE_ID = "default-workspace"
DEFAULT_PROJECT_ID = "bootstrap-project"


def bootstrap_platform_database() -> dict:
    create_platform_tables()

    db = PlatformSessionLocal()

    try:
        tenant = create_tenant(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            name="Default Tenant",
        )
        workspace = create_workspace(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )
        project = create_project(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            workspace_id=DEFAULT_WORKSPACE_ID,
            project_id=DEFAULT_PROJECT_ID,
            metadata={
                "source": "bootstrap",
            },
        )
        fetched_project = get_project(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            workspace_id=DEFAULT_WORKSPACE_ID,
            project_id=DEFAULT_PROJECT_ID,
        )

        return {
            "passed": fetched_project is not None,
            "tenant_id": tenant.tenant_id,
            "workspace_id": workspace.workspace_id,
            "project_id": project.project_id,
            "platform_tables_created": True,
        }

    finally:
        db.close()


def main() -> int:
    report = bootstrap_platform_database()
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
