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
