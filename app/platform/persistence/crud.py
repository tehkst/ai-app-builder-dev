import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.persistence.models import (
    PlatformGenerationRun,
    PlatformProject,
    PlatformTenant,
    PlatformWorkspace,
)


def utc_now():
    return datetime.now(timezone.utc)


def encode_metadata(metadata: Optional[Dict[str, Any]]) -> str:
    return json.dumps(metadata or {})


def get_tenant(db: Session, tenant_id: str) -> Optional[PlatformTenant]:
    return (
        db.query(PlatformTenant)
        .filter(PlatformTenant.tenant_id == tenant_id)
        .first()
    )


def create_tenant(
    db: Session,
    *,
    tenant_id: str,
    name: str,
    owner_id: Optional[str] = None,
    plan: str = "free",
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformTenant:
    existing = get_tenant(db, tenant_id)

    if existing:
        return existing

    tenant = PlatformTenant(
        tenant_id=tenant_id,
        name=name,
        owner_id=owner_id,
        plan=plan,
        metadata_json=encode_metadata(metadata),
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def get_workspace(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
) -> Optional[PlatformWorkspace]:
    return (
        db.query(PlatformWorkspace)
        .filter(
            PlatformWorkspace.tenant_id == tenant_id,
            PlatformWorkspace.workspace_id == workspace_id,
        )
        .first()
    )


def create_workspace(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    owner_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformWorkspace:
    existing = get_workspace(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )

    if existing:
        return existing

    workspace = PlatformWorkspace(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        metadata_json=encode_metadata(metadata),
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_project(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
) -> Optional[PlatformProject]:
    return (
        db.query(PlatformProject)
        .filter(
            PlatformProject.tenant_id == tenant_id,
            PlatformProject.workspace_id == workspace_id,
            PlatformProject.project_id == project_id,
        )
        .first()
    )


def create_project(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformProject:
    existing = get_project(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )

    if existing:
        return existing

    project = PlatformProject(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        metadata_json=encode_metadata(metadata),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project_generation_status(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
    generation_status: str,
) -> PlatformProject:
    project = get_project(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )

    if project is None:
        raise KeyError("Platform project was not found")

    project.generation_status = generation_status
    project.updated_at = utc_now()
    db.commit()
    db.refresh(project)
    return project


def increment_project_generation_count(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
) -> PlatformProject:
    project = get_project(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )

    if project is None:
        raise KeyError("Platform project was not found")

    project.generation_count += 1
    project.updated_at = utc_now()
    db.commit()
    db.refresh(project)
    return project


def increment_project_repair_count(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
) -> PlatformProject:
    project = get_project(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )

    if project is None:
        raise KeyError("Platform project was not found")

    project.repair_count += 1
    project.updated_at = utc_now()
    db.commit()
    db.refresh(project)
    return project


def create_generation_run(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformGenerationRun:
    run = PlatformGenerationRun(
        run_id=str(uuid4()),
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        status="started",
        metadata_json=encode_metadata(metadata),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_generation_run(db: Session, run_id: str) -> Optional[PlatformGenerationRun]:
    return (
        db.query(PlatformGenerationRun)
        .filter(PlatformGenerationRun.run_id == run_id)
        .first()
    )


def complete_generation_run(
    db: Session,
    *,
    run_id: str,
    review_status: Optional[str] = None,
    runtime_status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformGenerationRun:
    run = get_generation_run(db, run_id)

    if run is None:
        raise KeyError("Generation run was not found")

    run.status = "completed"
    run.review_status = review_status
    run.runtime_status = runtime_status
    run.completed_at = utc_now()
    run.updated_at = utc_now()

    if metadata is not None:
        run.metadata_json = encode_metadata(metadata)

    db.commit()
    db.refresh(run)
    return run


def fail_generation_run(
    db: Session,
    *,
    run_id: str,
    error_summary: str,
    review_status: Optional[str] = None,
    runtime_status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformGenerationRun:
    run = get_generation_run(db, run_id)

    if run is None:
        raise KeyError("Generation run was not found")

    run.status = "failed"
    run.review_status = review_status
    run.runtime_status = runtime_status
    run.error_summary = error_summary
    run.completed_at = utc_now()
    run.updated_at = utc_now()

    if metadata is not None:
        run.metadata_json = encode_metadata(metadata)

    db.commit()
    db.refresh(run)
    return run


def list_generation_runs_for_project(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
) -> List[PlatformGenerationRun]:
    return (
        db.query(PlatformGenerationRun)
        .filter(
            PlatformGenerationRun.tenant_id == tenant_id,
            PlatformGenerationRun.workspace_id == workspace_id,
            PlatformGenerationRun.project_id == project_id,
        )
        .order_by(PlatformGenerationRun.id.desc())
        .all()
    )
