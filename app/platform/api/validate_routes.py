import json

from starlette.requests import Request

from app.platform.api.routes import (
    list_generation_runs,
    list_projects,
    list_tenants,
    list_workspaces,
)
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables


def build_validation_request(path):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def validate_platform_api_routes():
    create_platform_tables()
    db = PlatformSessionLocal()

    try:
        tenants = list_tenants(request=build_validation_request("/platform/tenants"), db=db)
        workspaces = list_workspaces(request=build_validation_request("/platform/workspaces"), db=db)
        projects = list_projects(request=build_validation_request("/platform/projects"), db=db)
        generation_runs = list_generation_runs(request=build_validation_request("/platform/generation-runs"), db=db)

        passed = (
            "items" in tenants
            and "items" in workspaces
            and "items" in projects
            and "items" in generation_runs
            and isinstance(tenants["items"], list)
            and isinstance(workspaces["items"], list)
            and isinstance(projects["items"], list)
            and isinstance(generation_runs["items"], list)
        )

        return {
            "passed": passed,
            "tenant_count": len(tenants["items"]),
            "workspace_count": len(workspaces["items"]),
            "project_count": len(projects["items"]),
            "generation_run_count": len(generation_runs["items"]),
        }

    finally:
        db.close()


def main():
    report = validate_platform_api_routes()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
