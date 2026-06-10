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
