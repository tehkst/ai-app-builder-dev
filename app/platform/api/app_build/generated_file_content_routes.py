from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.app_build.schemas import GeneratedFileContentUpdateRequest
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.generated_file_persistence_service import update_persisted_generated_file_content
from app.platform.services.generated_file_version_diff_service import diff_generated_file_versions
from app.platform.services.generated_file_version_restore_plan_service import create_generated_file_version_restore_plan
from app.platform.services.generated_file_version_restore_simulation_service import simulate_generated_file_version_restore
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
    create_version_snapshots_for_workflow,
    get_generated_file_version,
    list_generated_file_versions,
)


router = APIRouter()


@router.put("/generated-files/{generated_file_id}/content")
def update_app_build_generated_file_content(
    generated_file_id: str,
    request: GeneratedFileContentUpdateRequest,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    update_result = update_persisted_generated_file_content(
        db,
        generated_file_id=generated_file_id,
        content_preview=request.content_preview,
        editor_id=request.editor_id,
    )

    if not update_result.get("found"):
        return update_result

    snapshot_result = create_generated_file_version_snapshot(
        db,
        generated_file_id,
        snapshot_status="browser_editor_snapshot",
        restore_status="not_restored",
        metadata={
            "snapshot_reason": "browser_workspace_file_editor_save",
            "editor_id": request.editor_id,
            "previous_content_hash": update_result.get("previous_content_hash"),
            "new_content_hash": update_result.get("content_hash"),
            "content_changed": update_result.get("content_changed"),
            "disk_write_performed": False,
            "generated_code_execution_performed": False,
        },
    )

    return {
        **update_result,
        "snapshot_created": snapshot_result.get("snapshot_created"),
        "generated_file_version": snapshot_result.get("generated_file_version"),
        "version_snapshot": snapshot_result,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
    }


@router.post("/runs/{workflow_run_id}/generated-file-versions")
def create_app_build_run_generated_file_versions(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return create_version_snapshots_for_workflow(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.post("/generated-files/{generated_file_id}/versions")
def create_app_build_generated_file_version(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return create_generated_file_version_snapshot(
        db,
        generated_file_id=generated_file_id,
    )


@router.get("/generated-files/{generated_file_id}/versions")
def list_app_build_generated_file_versions(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return list_generated_file_versions(
        db,
        generated_file_id=generated_file_id,
    )


@router.get("/generated-file-versions/{generated_file_version_id}")
def get_app_build_generated_file_version(
    generated_file_version_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_generated_file_version(
        db,
        generated_file_version_id=generated_file_version_id,
    )


@router.get("/generated-file-versions/{base_version_id}/diff/{target_version_id}")
def diff_app_build_generated_file_versions(
    base_version_id: str,
    target_version_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return diff_generated_file_versions(
        db,
        base_version_id=base_version_id,
        target_version_id=target_version_id,
    )


@router.post("/generated-file-versions/{target_version_id}/restore-plan")
def create_app_build_generated_file_version_restore_plan(
    target_version_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return create_generated_file_version_restore_plan(
        db,
        target_version_id=target_version_id,
    )


@router.get("/generated-file-versions/{target_version_id}/restore-simulation")
def simulate_app_build_generated_file_version_restore(
    target_version_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return simulate_generated_file_version_restore(
        db,
        target_version_id=target_version_id,
    )

