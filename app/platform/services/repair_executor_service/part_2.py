# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.platform.services.repair_approval_gate_service import assert_repair_apply_allowed
from app.platform.services.repair_plan_generator_service import generate_repair_plan_for_workflow
REPAIR_EXECUTOR_SAFETY_MODE = "repair_executor_v75_approval_gated_sandbox_only"
_ALLOWED_OPERATIONS = {"replace_file_content"}
_REPAIR_EXECUTION_HISTORY: Dict[str, List[Dict[str, Any]]] = {}

def execute_approved_repair(
    *,
    workflow_run_id: str,
    sandbox_root: str,
    operations: List[Dict[str, Any]],
    requested_by: str = "platform_admin",
) -> Dict[str, Any]:
    approval_gate = assert_repair_apply_allowed(workflow_run_id)
    if not approval_gate.get("apply_allowed"):
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            reason=approval_gate.get("block_reason") or "Repair execution is blocked until approval is granted.",
            approval_gate=approval_gate,
        )

    repair_plan_result = generate_repair_plan_for_workflow(workflow_run_id)
    repair_plan = repair_plan_result.get("repair_plan") or {}
    if not repair_plan.get("plan_needed"):
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            reason="Repair execution is blocked because no repair plan is needed.",
            approval_gate=approval_gate,
            repair_plan=repair_plan,
        )

    if not operations:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            reason="Repair execution requires at least one explicit operation.",
            approval_gate=approval_gate,
            repair_plan=repair_plan,
        )

    sandbox = Path(sandbox_root).expanduser().resolve()
    if not sandbox.exists() or not sandbox.is_dir():
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            reason="Approved sandbox root does not exist or is not a directory.",
            approval_gate=approval_gate,
            repair_plan=repair_plan,
        )

    allowed_targets = set(repair_plan.get("target_file_candidates") or [])
    executed_operations: List[Dict[str, Any]] = []

    try:
        for operation in operations:
            operation_name = operation.get("operation")
            if operation_name not in _ALLOWED_OPERATIONS:
                raise ValueError(f"Unsupported repair operation: {operation_name}")

            target_relative_path = operation.get("target_relative_path") or ""
            if allowed_targets and target_relative_path not in allowed_targets:
                raise ValueError("Repair target is not listed in the approved repair plan candidates.")

            replacement_content = operation.get("replacement_content")
            if not isinstance(replacement_content, str):
                raise ValueError("Replacement content must be a string.")

            target = _resolve_sandbox_file(sandbox, target_relative_path)
            before_exists = target.exists()
            before_content = target.read_text(encoding="utf-8") if before_exists else ""
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(replacement_content, encoding="utf-8")

            executed_operations.append(
                {
                    "operation": operation_name,
                    "target_relative_path": target_relative_path,
                    "target_absolute_path": str(target),
                    "before_exists": before_exists,
                    "after_exists": True,
                    "before_sha256": _sha256_text(before_content) if before_exists else None,
                    "after_sha256": _sha256_text(replacement_content),
                    "before_size_bytes": len(before_content.encode("utf-8")) if before_exists else 0,
                    "after_size_bytes": len(replacement_content.encode("utf-8")),
                    "reason": operation.get("reason"),
                }
            )
    except Exception as exc:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            reason=str(exc),
            approval_gate=approval_gate,
            repair_plan=repair_plan,
        )

    record = {
        "workflow_run_id": workflow_run_id,
        "execution_status": "applied",
        "applied": True,
        "requested_by": requested_by,
        "created_at": _now_iso(),
        "sandbox_root": str(sandbox),
        "operation_count": len(executed_operations),
        "operations": executed_operations,
        "repair_kind": repair_plan.get("repair_kind"),
        "failure_category": repair_plan.get("failure_category"),
    }
    _REPAIR_EXECUTION_HISTORY.setdefault(workflow_run_id, []).append(record)

    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_EXECUTOR_SAFETY_MODE,
        "execution_status": "applied",
        "applied": True,
        "blocked": False,
        "block_reason": None,
        "approval_gate": approval_gate,
        "repair_plan": repair_plan,
        "operations": executed_operations,
        "history": _REPAIR_EXECUTION_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(repair_applied=True, blocked=False),
    }

def get_repair_execution_history(workflow_run_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_EXECUTOR_SAFETY_MODE,
        "history": _REPAIR_EXECUTION_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(repair_applied=False, blocked=True),
    }

def reset_repair_execution_history_for_check() -> None:
    _REPAIR_EXECUTION_HISTORY.clear()
