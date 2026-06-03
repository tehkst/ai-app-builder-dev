import json

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import (
    PlatformAuditEvent,
    PlatformGenerationRun,
    PlatformProject,
    PlatformTenant,
    PlatformWorkspace,
)


def inspect_platform_database() -> dict:
    create_platform_tables()
    db = PlatformSessionLocal()

    try:
        tenants = db.query(PlatformTenant).order_by(PlatformTenant.id).all()
        workspaces = db.query(PlatformWorkspace).order_by(PlatformWorkspace.id).all()
        projects = db.query(PlatformProject).order_by(PlatformProject.id).all()
        generation_runs = (
            db.query(PlatformGenerationRun)
            .order_by(PlatformGenerationRun.id.desc())
            .all()
        )
        audit_events = (
            db.query(PlatformAuditEvent)
            .order_by(PlatformAuditEvent.id.desc())
            .limit(50)
            .all()
        )

        return {
            "tenant_count": len(tenants),
            "workspace_count": len(workspaces),
            "project_count": len(projects),
            "generation_run_count": len(generation_runs),
            "audit_event_count": len(audit_events),
            "tenants": [
                {
                    "tenant_id": tenant.tenant_id,
                    "name": tenant.name,
                    "status": tenant.status,
                    "plan": tenant.plan,
                    "owner_id": tenant.owner_id,
                }
                for tenant in tenants
            ],
            "workspaces": [
                {
                    "tenant_id": workspace.tenant_id,
                    "workspace_id": workspace.workspace_id,
                    "status": workspace.status,
                    "owner_id": workspace.owner_id,
                }
                for workspace in workspaces
            ],
            "projects": [
                {
                    "tenant_id": project.tenant_id,
                    "workspace_id": project.workspace_id,
                    "project_id": project.project_id,
                    "generation_status": project.generation_status,
                    "runtime_status": project.runtime_status,
                    "deployment_status": project.deployment_status,
                    "current_version": project.current_version,
                    "generation_count": project.generation_count,
                    "repair_count": project.repair_count,
                }
                for project in projects
            ],
            "generation_runs": [
                {
                    "run_id": generation_run.run_id,
                    "tenant_id": generation_run.tenant_id,
                    "workspace_id": generation_run.workspace_id,
                    "project_id": generation_run.project_id,
                    "status": generation_run.status,
                    "review_status": generation_run.review_status,
                    "runtime_status": generation_run.runtime_status,
                    "error_summary": generation_run.error_summary,
                    "started_at": generation_run.started_at,
                    "completed_at": generation_run.completed_at,
                }
                for generation_run in generation_runs
            ],
            "audit_events": [
                {
                    "event_type": audit_event.event_type,
                    "actor_type": audit_event.actor_type,
                    "actor_id": audit_event.actor_id,
                    "tenant_id": audit_event.tenant_id,
                    "workspace_id": audit_event.workspace_id,
                    "project_id": audit_event.project_id,
                    "status": audit_event.status,
                    "route": audit_event.route,
                    "auth_mode": audit_event.auth_mode,
                    "created_at": audit_event.created_at,
                }
                for audit_event in audit_events
            ],
        }

    finally:
        db.close()


def main() -> int:
    report = inspect_platform_database()
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
