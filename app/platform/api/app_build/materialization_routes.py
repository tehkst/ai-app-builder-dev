from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.manual_browser_test_harness_service import prepare_manual_browser_test_harness
from app.platform.services.materialization_approval_record_service import (
    create_materialization_approval_record,
    get_latest_materialization_approval_record,
)
from app.platform.services.materialization_dry_run_service import build_materialization_dry_run
from app.platform.services.materialization_execution_gate_service import attempt_materialization_execution
from app.platform.services.materialization_sandbox_writer_service import write_generated_file_to_local_sandbox


router = APIRouter()


@router.post("/generated-files/{generated_file_id}/local-sandbox-materializations")
def write_generated_file_to_local_sandbox_route(
    generated_file_id: str,
    db: Session = Depends(get_platform_db),
    _admin: bool = Depends(require_platform_admin),
):
    return write_generated_file_to_local_sandbox(
        db,
        generated_file_id=generated_file_id,
    )


@router.get("/generated-files/{generated_file_id}/manual-browser-test-harness")
def prepare_manual_browser_test_harness_route(
    generated_file_id: str,
    db: Session = Depends(get_platform_db),
    _admin: bool = Depends(require_platform_admin),
):
    return prepare_manual_browser_test_harness(
        db,
        generated_file_id=generated_file_id,
    )


@router.post("/generated-files/{generated_file_id}/materialization-dry-runs")
def build_materialization_dry_run_route(
    generated_file_id: str,
    db: Session = Depends(get_platform_db),
    _admin: bool = Depends(require_platform_admin),
):
    return build_materialization_dry_run(
        db,
        generated_file_id=generated_file_id,
    )


@router.post("/generated-files/{generated_file_id}/materialization-execution-attempts")
def attempt_materialization_execution_route(
    generated_file_id: str,
    db: Session = Depends(get_platform_db),
    _admin: bool = Depends(require_platform_admin),
):
    return attempt_materialization_execution(
        db,
        generated_file_id=generated_file_id,
    )


@router.post("/generated-files/{generated_file_id}/materialization-approval-records")
def create_materialization_approval_record_route(
    generated_file_id: str,
    payload: dict = None,
    db: Session = Depends(get_platform_db),
    _admin: bool = Depends(require_platform_admin),
):
    payload = payload or {}
    return create_materialization_approval_record(
        db,
        generated_file_id=generated_file_id,
        approved_by=str(payload.get("approved_by") or "platform_admin"),
        approval_reason=payload.get("approval_reason"),
    )


@router.get("/generated-files/{generated_file_id}/materialization-approval-records/latest")
def get_latest_materialization_approval_record_route(
    generated_file_id: str,
    db: Session = Depends(get_platform_db),
    _admin: bool = Depends(require_platform_admin),
):
    return get_latest_materialization_approval_record(
        db,
        generated_file_id=generated_file_id,
    )

