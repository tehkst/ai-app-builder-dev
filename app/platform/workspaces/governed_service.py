from __future__ import annotations

from typing import Any, Dict

from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome
from app.platform.workspaces.execution_service import (
    acquire_workspace_lease, cleanup_expired_workspaces, create_workspace,
    destroy_workspace, recover_workspace,
)


def execute_workspace_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = str(payload.get("action") or "").strip()
    handlers = {
        "create": lambda: create_workspace(payload), "resume": lambda: recover_workspace(payload),
        "lock": lambda: acquire_workspace_lease(payload),
        "recover": lambda: recover_workspace(payload), "cleanup": lambda: cleanup_expired_workspaces(payload),
        "destroy": lambda: destroy_workspace(payload),
    }
    if action not in handlers: return {"status": "blocked", "error": "Unsupported workspace action."}
    capability = "workspace_%s" % ({"create": "create", "resume": "resume", "lock": "lock", "recover": "recover", "cleanup": "cleanup", "destroy": "destroy"}[action])
    decision = authorize_governed_action(payload, capability, policy_context={"durable_approval_required": True, "workspace_ownership": True, "platform_state": True})
    if not decision.get("allowed"): return {"status": "blocked", "authorization": decision, "error": decision.get("reason")}
    result = handlers[action]()
    result["governance_evidence"] = record_governed_outcome(payload, decision, result)
    return result
