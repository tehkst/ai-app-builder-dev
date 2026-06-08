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


def _safety_flags() -> Dict[str, bool]:
    return {
        "approval_gate_only": True,
        "runtime_execution_enabled": False,
        "install_packages_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_code_execution_performed": False,
        "node_command_executed": False,
        "python_command_executed": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "repair_applied": False,
        "restore_executed": False,
    }


def _safe_metadata(record: PlatformRuntimeApprovalRecord) -> Dict[str, Any]:
    try:
        data = json.loads(record.metadata_json or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _record_to_dict(record: PlatformRuntimeApprovalRecord) -> Dict[str, Any]:
    return {
        "runtime_approval_record_id": record.runtime_approval_record_id,
        "workflow_run_id": record.workflow_run_id,
        "selected_generated_file_id": record.selected_generated_file_id,
        "approval_status": record.approval_status,
        "approval_action": record.approval_action,
        "approval_token": record.approval_token,
        "approved_by": record.approved_by,
        "approval_reason": record.approval_reason,
        "run_plan_status": record.run_plan_status,
        "framework_type": record.framework_type,
        "working_directory": record.working_directory,
        "install_command": record.install_command,
        "run_command": record.run_command,
        "runtime_port": record.runtime_port,
        "safety_mode": record.safety_mode,
        "approval_record_only": record.approval_record_only,
        "runtime_execution_enabled": record.runtime_execution_enabled,
        "install_packages_performed": record.install_packages_performed,
        "runtime_server_started": record.runtime_server_started,
        "preview_server_started": record.preview_server_started,
        "generated_code_execution_performed": record.generated_code_execution_performed,
        "node_command_executed": record.node_command_executed,
        "python_command_executed": record.python_command_executed,
        "generated_files_written": record.generated_files_written,
        "filesystem_write_performed": record.filesystem_write_performed,
        "disk_write_performed": record.disk_write_performed,
        "repair_applied": record.repair_applied,
        "restore_executed": record.restore_executed,
        "metadata": _safe_metadata(record),
        "approved_at": record.approved_at.isoformat() if record.approved_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _empty_response(workflow_run_id: Optional[str], selected_generated_file_id: Optional[str]) -> Dict[str, Any]:
    return {
        "success": True,
        "found": False,
        "workflow_run_id": workflow_run_id,
        "selected_generated_file_id": selected_generated_file_id,
        "approval_record": None,
        "safety_flags": _safety_flags(),
        "safety_mode": RUNTIME_APPROVAL_SAFETY_MODE,
    }


def _create_record_from_run_plan(
    db: Session,
    run_plan_result: Dict[str, Any],
    approval_action: str,
    approved_by: str = "platform_admin",
    approval_reason: Optional[str] = None,
) -> Dict[str, Any]:
    plan = run_plan_result.get("runtime_run_plan") or {}
    install_step = plan.get("install_step") or {}
    run_step = plan.get("run_step") or {}
    now = utc_now()
    is_approved = approval_action == "approve"

    record = PlatformRuntimeApprovalRecord(
        runtime_approval_record_id="runtime_approval_" + uuid4().hex,
        workflow_run_id=run_plan_result.get("workflow_run_id"),
        selected_generated_file_id=run_plan_result.get("selected_generated_file_id"),
        workspace_id=None,
        project_id=None,
        approval_status="approved" if is_approved else "rejected",
        approval_action=approval_action,
        approval_token="runtime-approval-gate-" + uuid4().hex,
        approved_by=approved_by,
        approval_reason=approval_reason or "V69 runtime approval gate record only. No runtime action is performed.",
        run_plan_status=plan.get("status"),
        framework_type=plan.get("framework_type"),
        working_directory=plan.get("working_directory"),
        install_command=install_step.get("command"),
        run_command=run_step.get("command"),
        runtime_port=run_step.get("port") or plan.get("port"),
        safety_mode=RUNTIME_APPROVAL_SAFETY_MODE,
        approval_record_only=True,
        runtime_execution_enabled=False,
        install_packages_performed=False,
        runtime_server_started=False,
        preview_server_started=False,
        generated_code_execution_performed=False,
        node_command_executed=False,
        python_command_executed=False,
        generated_files_written=False,
        filesystem_write_performed=False,
        disk_write_performed=False,
        repair_applied=False,
        restore_executed=False,
        metadata_json=json.dumps(
            {
                "source": "v69_runtime_approval_gate",
                "approval_gate_only": True,
                "run_plan": plan,
            },
            sort_keys=True,
        ),
        approved_at=now if is_approved else None,
        created_at=now,
        updated_at=now,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "found": True,
        "record_created": True,
        "workflow_run_id": run_plan_result.get("workflow_run_id"),
        "selected_generated_file_id": run_plan_result.get("selected_generated_file_id"),
        "approval_record": _record_to_dict(record),
        "source_runtime_run_plan": run_plan_result,
        "safety_flags": _safety_flags(),
        "safety_mode": RUNTIME_APPROVAL_SAFETY_MODE,
    }


def approve_runtime_run_plan_for_workflow(
    db: Session,
    workflow_run_id: str,
    approved_by: str = "platform_admin",
    approval_reason: Optional[str] = None,
) -> Dict[str, Any]:
    run_plan_result = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
    if not run_plan_result.get("found"):
        return _empty_response(workflow_run_id, None)
    return _create_record_from_run_plan(db, run_plan_result, "approve", approved_by, approval_reason)


def reject_runtime_run_plan_for_workflow(
    db: Session,
    workflow_run_id: str,
    approved_by: str = "platform_admin",
    approval_reason: Optional[str] = None,
) -> Dict[str, Any]:
    run_plan_result = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
    if not run_plan_result.get("found"):
        return _empty_response(workflow_run_id, None)
    return _create_record_from_run_plan(db, run_plan_result, "reject", approved_by, approval_reason)


def get_latest_runtime_approval_for_workflow(db: Session, workflow_run_id: str) -> Dict[str, Any]:
    record = (
        db.query(PlatformRuntimeApprovalRecord)
        .filter(PlatformRuntimeApprovalRecord.workflow_run_id == workflow_run_id)
        .order_by(PlatformRuntimeApprovalRecord.created_at.desc())
        .first()
    )
    if not record:
        return _empty_response(workflow_run_id, None)
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "selected_generated_file_id": record.selected_generated_file_id,
        "approval_record": _record_to_dict(record),
        "safety_flags": _safety_flags(),
        "safety_mode": RUNTIME_APPROVAL_SAFETY_MODE,
    }


def approve_runtime_run_plan_for_generated_file(
    db: Session,
    generated_file_id: str,
    approved_by: str = "platform_admin",
    approval_reason: Optional[str] = None,
) -> Dict[str, Any]:
    run_plan_result = build_runtime_run_plan_for_generated_file(db, generated_file_id=generated_file_id)
    if not run_plan_result.get("found"):
        return _empty_response(None, generated_file_id)
    return _create_record_from_run_plan(db, run_plan_result, "approve", approved_by, approval_reason)


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
