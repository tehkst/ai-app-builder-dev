# Split from the legacy module to keep each Python file under 200 lines.
import json
from typing import Any, Dict, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from app.platform.persistence.models import PlatformRuntimeApprovalRecord, utc_now
from app.platform.services.runtime_run_plan_builder_service import (
    build_runtime_run_plan_for_generated_file,
    build_runtime_run_plan_for_workflow,
)
RUNTIME_APPROVAL_SAFETY_MODE = "runtime_approval_gate_only_no_execution"

def reject_runtime_run_plan_for_generated_file(
    db: Session,
    generated_file_id: str,
    approved_by: str = "platform_admin",
    approval_reason: Optional[str] = None,
) -> Dict[str, Any]:
    run_plan_result = build_runtime_run_plan_for_generated_file(db, generated_file_id=generated_file_id)
    if not run_plan_result.get("found"):
        return _empty_response(None, generated_file_id)
    return _create_record_from_run_plan(db, run_plan_result, "reject", approved_by, approval_reason)

def get_latest_runtime_approval_for_generated_file(db: Session, generated_file_id: str) -> Dict[str, Any]:
    record = (
        db.query(PlatformRuntimeApprovalRecord)
        .filter(PlatformRuntimeApprovalRecord.selected_generated_file_id == generated_file_id)
        .order_by(PlatformRuntimeApprovalRecord.created_at.desc())
        .first()
    )
    if not record:
        return _empty_response(None, generated_file_id)
    return {
        "success": True,
        "found": True,
        "workflow_run_id": record.workflow_run_id,
        "selected_generated_file_id": generated_file_id,
        "approval_record": _record_to_dict(record),
        "safety_flags": _safety_flags(),
        "safety_mode": RUNTIME_APPROVAL_SAFETY_MODE,
    }
