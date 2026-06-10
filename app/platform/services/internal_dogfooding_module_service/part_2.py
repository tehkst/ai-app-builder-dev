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

def inspect_internal_dogfooding_module(
    *,
    request_id: str,
) -> Dict[str, Any]:
    handoff = inspect_self_build_module_request_handoff(request_id)
    rollout_gate = inspect_module_rollout_gate(request_id)
    _history_event(
        request_id,
        "dogfooding_module_inspected",
        {
            "handoff_status": (handoff.get("request") or {}).get("handoff_status"),
            "rollout_status": rollout_gate.get("rollout_status"),
            "eligible": rollout_gate.get("eligible"),
        },
    )
    return {
        "success": True,
        "safety_mode": INTERNAL_DOGFOODING_MODULE_SAFETY_MODE,
        "request_id": request_id,
        "handoff": handoff,
        "rollout_gate": rollout_gate,
        "history": _INTERNAL_DOGFOODING_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(rollout_gate_checked=True),
    }

def decide_internal_dogfooding_rollout(
    *,
    request_id: str,
    decision: str,
    decided_by: str = "platform_admin",
    reason: Any = None,
) -> Dict[str, Any]:
    normalized_decision = str(decision or "").strip().lower()
    if normalized_decision == "approve":
        decision_result = approve_module_rollout(
            request_id=request_id,
            approved_by=decided_by,
            reason=reason,
        )
        action = "dogfooding_rollout_approval_recorded"
    elif normalized_decision == "reject":
        decision_result = reject_module_rollout(
            request_id=request_id,
            rejected_by=decided_by,
            reason=reason,
        )
        action = "dogfooding_rollout_rejection_recorded"
    else:
        decision_result = inspect_module_rollout_gate(request_id)
        decision_result["rollout_status"] = "invalid_decision"
        action = "dogfooding_rollout_decision_invalid"

    _history_event(
        request_id,
        action,
        {
            "decision": normalized_decision,
            "decided_by": decided_by,
            "rollout_status": decision_result.get("rollout_status"),
        },
    )
    return {
        "success": True,
        "safety_mode": INTERNAL_DOGFOODING_MODULE_SAFETY_MODE,
        "request_id": request_id,
        "decision": normalized_decision,
        "decision_result": decision_result,
        "history": _INTERNAL_DOGFOODING_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(
            rollout_gate_checked=True,
            rollout_decision_recorded=normalized_decision in {"approve", "reject"},
        ),
    }

def get_internal_dogfooding_module_history(request_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "safety_mode": INTERNAL_DOGFOODING_MODULE_SAFETY_MODE,
        "request_id": request_id,
        "history": _INTERNAL_DOGFOODING_HISTORY.get(request_id, []),
        "safety_flags": _safe_flags(),
    }

def reset_internal_dogfooding_module_for_check() -> None:
    _INTERNAL_DOGFOODING_HISTORY.clear()
