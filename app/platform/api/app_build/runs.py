from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.agents.app_build_request_run_check import run_app_build_request
from app.platform.api.app_build.schemas import AppBuildRunRequest
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.generated_file_persistence_service import list_persisted_generated_files
from app.platform.services.generated_file_rollback_service import extract_generated_files_from_workflow_detail
from app.platform.services.workflow_run_persistence_service import (
    compact_workflow_run_summary,
    get_workflow_run_detail,
    list_recent_workflow_runs,
)


router = APIRouter()


@router.post("/run")
def run_app_build(
    request: AppBuildRunRequest,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return run_app_build_request(
        app_request=request.app_request,
        scoping_request_id=request.scoping_request_id,
        workflow_name=request.workflow_name,
        real_bridge=request.real_bridge,
    )


@router.get("/runs/recent")
def list_recent_app_build_runs(
    limit: int = 10,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    return {
        "success": True,
        "limit": safe_limit,
        "workflow_runs": list_recent_workflow_runs(
            db,
            limit=safe_limit,
        ),
    }


@router.get("/runs/{workflow_run_id}/summary")
def get_app_build_run_summary(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    detail = get_workflow_run_detail(
        db,
        workflow_run_id=workflow_run_id,
    )
    return compact_workflow_run_summary(detail)


@router.get("/runs/{workflow_run_id}/detail")
def get_app_build_run_detail(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_workflow_run_detail(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/generated-files")
def get_app_build_run_generated_files(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    detail = get_workflow_run_detail(
        db,
        workflow_run_id=workflow_run_id,
    )
    generated_files = extract_generated_files_from_workflow_detail(detail)

    return {
        "success": True,
        "found": detail.get("found", False),
        "workflow_run_id": workflow_run_id,
        "workflow_name": detail.get("workflow_name"),
        "workflow_status": detail.get("status"),
        "generated_file_count": len(generated_files),
        "generated_files": generated_files,
    }


@router.get("/runs/{workflow_run_id}/persisted-files")
def get_app_build_run_persisted_files(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return list_persisted_generated_files(
        db,
        workflow_run_id=workflow_run_id,
    )

