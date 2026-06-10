from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.generated_file_persistence_service import get_persisted_generated_file
from app.platform.services.runtime_approval_gate_service import (
    approve_runtime_run_plan_for_generated_file,
    get_latest_runtime_approval_for_generated_file,
    reject_runtime_run_plan_for_generated_file,
)
from app.platform.services.runtime_readiness_detector_service import detect_runtime_readiness_for_generated_file
from app.platform.services.runtime_run_plan_builder_service import build_runtime_run_plan_for_generated_file


router = APIRouter()


@router.get("/generated-files/{generated_file_id}")
def get_app_build_persisted_generated_file(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_persisted_generated_file(
        db,
        generated_file_id=generated_file_id,
    )


@router.get("/generated-files/{generated_file_id}/runtime-readiness")
def inspect_generated_file_runtime_readiness(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return detect_runtime_readiness_for_generated_file(
        db,
        generated_file_id=generated_file_id,
    )


@router.get("/generated-files/{generated_file_id}/runtime-run-plan")
def build_generated_file_runtime_run_plan(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return build_runtime_run_plan_for_generated_file(
        db,
        generated_file_id=generated_file_id,
    )


@router.post("/generated-files/{generated_file_id}/runtime-approval/approve")
def approve_generated_file_runtime_approval(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return approve_runtime_run_plan_for_generated_file(
        db,
        generated_file_id=generated_file_id,
    )


@router.post("/generated-files/{generated_file_id}/runtime-approval/reject")
def reject_generated_file_runtime_approval(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return reject_runtime_run_plan_for_generated_file(
        db,
        generated_file_id=generated_file_id,
    )


@router.get("/generated-files/{generated_file_id}/runtime-approval/latest")
def get_generated_file_latest_runtime_approval(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_latest_runtime_approval_for_generated_file(
        db,
        generated_file_id=generated_file_id,
    )

