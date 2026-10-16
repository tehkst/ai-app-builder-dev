"""Founder-only repair flow for customer app builds, on the production server.

Moved from `app/main.py`'s `/platform/app-build/*` routes (clean-up batch 4), which production
never served and which used a separate platform-admin login. Same services, same order:
overview -> propose (Nautilus, on a scratch copy; no generated code runs) -> approve/reject ->
apply -> rerun. Every call needs a Mission Control founder session token in the body, and the
founder's email is recorded as the actor. The sandbox is always resolved from the workflow run.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from app.platform.auth.service import require_founder

CONTRACT = "repair-console-v1"


def _guarded(payload: Dict[str, Any], action: Callable[[str, str], Dict[str, Any]]) -> Dict[str, Any]:
    founder = require_founder(payload or {})
    if not founder.get("authorized"):
        return {"contract": CONTRACT, "status": "unauthorized", "authenticated": False}
    workflow_run_id = str((payload or {}).get("workflow_run_id") or "").strip()
    if not workflow_run_id:
        return {"contract": CONTRACT, "status": "invalid-request", "error": "workflow_run_id is required."}
    result = action(workflow_run_id, str(founder.get("email") or "founder"))
    return {"contract": CONTRACT, "workflow_run_id": workflow_run_id, **result}


def _with_db(fn: Callable[..., Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables

    create_platform_tables()
    with PlatformSessionLocal() as db:
        return fn(db=db, **kwargs)


def repair_overview(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Where the run's repair stands: loop status, plan, approval, Nautilus proposals, history."""
    def action(run_id: str, _: str) -> Dict[str, Any]:
        from app.platform.services.nautilus_repair_service import get_nautilus_repair_proposals
        from app.platform.services.repair_approval_gate_service import get_repair_approval_status
        from app.platform.services.repair_executor_service import get_repair_execution_history
        from app.platform.services.repair_plan_generator_service import generate_repair_plan_for_workflow
        from app.platform.services.repair_rerun_coordinator_service import get_repair_rerun_history
        from app.platform.services.self_healing_loop_coordinator_service import inspect_self_healing_loop

        return {
            "status": "ready",
            "loop": inspect_self_healing_loop(workflow_run_id=run_id),
            "plan": generate_repair_plan_for_workflow(workflow_run_id=run_id),
            "approval": get_repair_approval_status(workflow_run_id=run_id),
            "proposals": get_nautilus_repair_proposals(run_id),
            "executions": get_repair_execution_history(workflow_run_id=run_id),
            "reruns": get_repair_rerun_history(workflow_run_id=run_id),
        }
    return _guarded(payload, action)


def repair_propose(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.services.nautilus_repair_service import propose_nautilus_repair

    return _guarded(payload, lambda run_id, who: _with_db(propose_nautilus_repair, workflow_run_id=run_id, requested_by=who))


def repair_approve(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.services.repair_approval_gate_service import approve_repair_plan

    return _guarded(payload, lambda run_id, who: approve_repair_plan(workflow_run_id=run_id, approved_by=who))


def repair_reject(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.services.repair_approval_gate_service import reject_repair_plan

    return _guarded(payload, lambda run_id, who: reject_repair_plan(workflow_run_id=run_id, rejected_by=who))


def repair_apply(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.services.nautilus_repair_service import apply_nautilus_repair_proposal

    proposal_id = str((payload or {}).get("proposal_id") or "") or None
    return _guarded(payload, lambda run_id, who: apply_nautilus_repair_proposal(
        workflow_run_id=run_id, proposal_id=proposal_id, requested_by=who))


def repair_rerun(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.services.repair_rerun_coordinator_service import rerun_after_successful_repair

    perform_install = bool((payload or {}).get("perform_install") or False)
    return _guarded(payload, lambda run_id, who: _with_db(
        rerun_after_successful_repair, workflow_run_id=run_id, requested_by=who, perform_install=perform_install))
