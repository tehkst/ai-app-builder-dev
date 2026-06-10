# Split from the legacy module to keep each Python file under 200 lines.
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
