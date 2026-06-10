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

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _safe_flags(*, repair_applied: bool = False, blocked: bool = True) -> Dict[str, bool]:
    return {
        "repair_executor_checked": True,
        "approval_gate_checked_before_apply": True,
        "repair_apply_blocked": blocked,
        "repair_applied": repair_applied,
        "sandbox_bound_repair_only": True,
        "auto_approval_performed": False,
        "restore_executed": False,
        "module_rollout_performed": False,
        "generated_code_execution_performed": False,
        "install_packages_performed": False,
        "node_command_executed": False,
        "python_command_executed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "process_started": False,
    }

def _blocked_result(
    *,
    workflow_run_id: str,
    reason: str,
    approval_gate: Optional[Dict[str, Any]] = None,
    repair_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": REPAIR_EXECUTOR_SAFETY_MODE,
        "execution_status": "blocked",
        "applied": False,
        "blocked": True,
        "block_reason": reason,
        "approval_gate": approval_gate,
        "repair_plan": repair_plan,
        "operations": [],
        "history": _REPAIR_EXECUTION_HISTORY.get(workflow_run_id, []),
        "safety_flags": _safe_flags(repair_applied=False, blocked=True),
    }

def _resolve_sandbox_file(sandbox_root: Path, relative_path: str) -> Path:
    if not relative_path or relative_path.startswith("/"):
        raise ValueError("Repair target must be a relative sandbox path.")
    target = (sandbox_root / relative_path).resolve()
    root = sandbox_root.resolve()
    if root != target and root not in target.parents:
        raise ValueError("Repair target must stay inside the approved sandbox root.")
    return target

def build_replace_file_operation(
    *,
    target_relative_path: str,
    replacement_content: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "operation": "replace_file_content",
        "target_relative_path": target_relative_path,
        "replacement_content": replacement_content,
        "reason": reason,
    }
