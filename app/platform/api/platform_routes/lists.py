from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.api.platform_routes.shared import clamp_limit
from app.platform.persistence.database import get_platform_db
from app.platform.persistence.models import (
    PlatformGenerationRun,
    PlatformProject,
    PlatformTenant,
    PlatformWorkspace,
)
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter


router = APIRouter()


@router.get("/tenants")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_tenants(request: Request, limit: int = 50, db: Session = Depends(get_platform_db)):
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
    workspaces = db.query(PlatformWorkspace).order_by(PlatformWorkspace.id.desc()).limit(safe_limit).all()
    return {
        "items": [
            {
                "tenant_id": item.tenant_id,
                "workspace_id": item.workspace_id,
                "status": item.status,
                "owner_id": item.owner_id,
            }
            for item in workspaces
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
                "tenant_id": item.tenant_id,
                "workspace_id": item.workspace_id,
                "project_id": item.project_id,
                "generation_status": item.generation_status,
                "runtime_status": item.runtime_status,
                "deployment_status": item.deployment_status,
                "current_version": item.current_version,
                "generation_count": item.generation_count,
                "repair_count": item.repair_count,
            }
            for item in projects
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
    runs = db.query(PlatformGenerationRun).order_by(PlatformGenerationRun.id.desc()).limit(safe_limit).all()
    return {
        "items": [
            {
                "run_id": item.run_id,
                "tenant_id": item.tenant_id,
                "workspace_id": item.workspace_id,
                "project_id": item.project_id,
                "status": item.status,
                "review_status": item.review_status,
                "runtime_status": item.runtime_status,
                "error_summary": item.error_summary,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
            }
            for item in runs
        ],
        "limit": safe_limit,
    }
