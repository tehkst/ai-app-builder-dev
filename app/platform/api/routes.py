from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter
from app.platform.persistence.models import (
    PlatformGenerationRun,
    PlatformProject,
    PlatformTenant,
    PlatformWorkspace,
)


router = APIRouter(prefix="/platform", tags=["platform"])


MAX_LIST_LIMIT = 100


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1

    if limit > MAX_LIST_LIMIT:
        return MAX_LIST_LIMIT

    return limit


@router.get("/tenants")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_tenants(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    tenants = db.query(PlatformTenant).order_by(PlatformTenant.id.desc()).limit(safe_limit).all()

    return {
        "items": [
            {
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
                "status": tenant.status,
                "plan": tenant.plan,
                "owner_id": tenant.owner_id,
            }
            for tenant in tenants
        ],
        "limit": safe_limit,
    }


@router.get("/workspaces")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_workspaces(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    workspaces = (
        db.query(PlatformWorkspace)
        .order_by(PlatformWorkspace.id.desc())
        .limit(safe_limit)
        .all()
    )

    return {
        "items": [
            {
                "tenant_id": workspace.tenant_id,
                "workspace_id": workspace.workspace_id,
                "status": workspace.status,
                "owner_id": workspace.owner_id,
            }
            for workspace in workspaces
        ],
        "limit": safe_limit,
    }


@router.get("/projects")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_projects(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    projects = db.query(PlatformProject).order_by(PlatformProject.id.desc()).limit(safe_limit).all()

    return {
        "items": [
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
        "limit": safe_limit,
    }


@router.get("/generation-runs")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_generation_runs(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    generation_runs = (
        db.query(PlatformGenerationRun)
        .order_by(PlatformGenerationRun.id.desc())
        .limit(safe_limit)
        .all()
    )

    return {
        "items": [
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
        "limit": safe_limit,
    }
