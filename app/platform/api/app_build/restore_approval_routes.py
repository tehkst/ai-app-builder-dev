from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.app_build.schemas import RestoreApprovalDecisionRequest
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.generated_file_version_restore_approval_service import (
    approve_generated_file_version_restore_approval_request,
    create_generated_file_version_restore_approval_request,
    get_generated_file_version_restore_approval_request,
    reject_generated_file_version_restore_approval_request,
)
from app.platform.services.generated_file_version_restore_execution_service import execute_approved_generated_file_version_restore


router = APIRouter()


@router.post("/restore-approval-requests/{approval_id}/execute")
def execute_app_build_generated_file_version_restore(
    approval_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return execute_approved_generated_file_version_restore(
        db,
        approval_id=approval_id,
    )


@router.post("/generated-file-versions/{target_version_id}/restore-approval-requests")
def create_app_build_generated_file_version_restore_approval_request(
    target_version_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return create_generated_file_version_restore_approval_request(
        db,
        target_version_id=target_version_id,
    )


@router.get("/restore-approval-requests/{approval_id}")
def get_app_build_generated_file_version_restore_approval_request(
    approval_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_generated_file_version_restore_approval_request(
        db,
        approval_id=approval_id,
    )


@router.post("/restore-approval-requests/{approval_id}/approve")
def approve_app_build_generated_file_version_restore_approval_request(
    approval_id: str,
    request: Optional[RestoreApprovalDecisionRequest] = None,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    request = request or RestoreApprovalDecisionRequest()
    return approve_generated_file_version_restore_approval_request(
        db,
        approval_id=approval_id,
        approver_id=request.approver_id,
        decision_note=request.decision_note,
    )


@router.post("/restore-approval-requests/{approval_id}/reject")
def reject_app_build_generated_file_version_restore_approval_request(
    approval_id: str,
    request: Optional[RestoreApprovalDecisionRequest] = None,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    request = request or RestoreApprovalDecisionRequest()
    return reject_generated_file_version_restore_approval_request(
        db,
        approval_id=approval_id,
        approver_id=request.approver_id,
        decision_note=request.decision_note,
    )

