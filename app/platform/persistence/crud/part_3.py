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
