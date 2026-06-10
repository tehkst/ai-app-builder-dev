# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.platform.services.module_rollout_gate_service import (
    approve_module_rollout,
    inspect_module_rollout_gate,
    reject_module_rollout,
)
from app.platform.services.self_build_module_request_service import (
    create_self_build_module_request,
    inspect_self_build_module_request_handoff,
    link_self_build_module_request_to_workflow,
)
INTERNAL_DOGFOODING_MODULE_SAFETY_MODE = "internal_dogfooding_module_v80_demonstration_only"
_INTERNAL_DOGFOODING_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
DEFAULT_DOGFOODING_MODULE = {
    "module_name": "Internal Approval Checklist",
    "module_goal": "Show a small internal checklist for approval-gated module requests and rollout readiness.",
    "acceptance_criteria": [
        "Shows module request summary",
        "Shows self-healing loop handoff status",
        "Shows rollout gate status",
        "Does not execute rollout",
    ],
    "notes": "V80 dogfooding demonstration only; no production deployment.",
}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _safe_flags(*, rollout_gate_checked: bool = False, rollout_decision_recorded: bool = False) -> Dict[str, bool]:
    return {
        "internal_dogfooding_checked": True,
        "dogfooding_demonstration_only": True,
        "module_request_created": True,
        "rollout_gate_checked": rollout_gate_checked,
        "rollout_decision_recorded": rollout_decision_recorded,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "production_file_write_performed": False,
        "live_module_modified": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "install_packages_performed": False,
        "auto_approval_performed": False,
        "approval_bypass_performed": False,
        "repair_applied": False,
        "unapproved_repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
        "rollout_execution_performed": False,
    }

def _history_event(request_id: str, action: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    event = {
        "request_id": request_id,
        "action": action,
        "created_at": _now_iso(),
        "details": details or {},
    }
    _INTERNAL_DOGFOODING_HISTORY.setdefault(request_id, []).append(event)
    return event

def create_internal_dogfooding_module_request(
    *,
    requested_by: str = "platform_admin",
    workflow_run_id: Optional[str] = None,
    module_name: Any = None,
    module_goal: Any = None,
    acceptance_criteria: Optional[List[Any]] = None,
    notes: Any = None,
) -> Dict[str, Any]:
    module = DEFAULT_DOGFOODING_MODULE.copy()
    if module_name is not None:
        module["module_name"] = module_name
    if module_goal is not None:
        module["module_goal"] = module_goal
    if acceptance_criteria is not None:
        module["acceptance_criteria"] = acceptance_criteria
    if notes is not None:
        module["notes"] = notes

    created = create_self_build_module_request(
        module_name=module["module_name"],
        module_goal=module["module_goal"],
        requested_by=requested_by,
        workflow_run_id=workflow_run_id,
        acceptance_criteria=module["acceptance_criteria"],
        notes=module["notes"],
    )
    request_id = (created.get("request") or {}).get("request_id")
    _history_event(
        request_id,
        "dogfooding_module_request_created",
        {
            "requested_by": requested_by,
            "workflow_run_id": workflow_run_id,
            "module_name": (created.get("request") or {}).get("module_name"),
        },
    )
    return {
        "success": True,
        "safety_mode": INTERNAL_DOGFOODING_MODULE_SAFETY_MODE,
        "request_id": request_id,
        "dogfooding_module": module,
        "module_request": created,
        "history": _INTERNAL_DOGFOODING_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(),
    }

def link_internal_dogfooding_module_to_workflow(
    *,
    request_id: str,
    workflow_run_id: str,
    linked_by: str = "platform_admin",
) -> Dict[str, Any]:
    linked = link_self_build_module_request_to_workflow(
        request_id=request_id,
        workflow_run_id=workflow_run_id,
        linked_by=linked_by,
    )
    _history_event(
        request_id,
        "dogfooding_module_linked_to_workflow",
        {"workflow_run_id": workflow_run_id, "linked_by": linked_by},
    )
    return {
        "success": True,
        "safety_mode": INTERNAL_DOGFOODING_MODULE_SAFETY_MODE,
        "request_id": request_id,
        "workflow_run_id": workflow_run_id,
        "module_request": linked,
        "history": _INTERNAL_DOGFOODING_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(),
    }
