from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.services.agent_workflow_audit import log_workflow_event
from app.platform.services.agent_workflow_limits import (
    MAX_CONTEXT_JSON_BYTES,
    MAX_HANDLER_RESULT_JSON_BYTES,
    MAX_STEP_DEPENDENCIES,
    MAX_WORKFLOW_STEPS,
)
from app.platform.services.workflow_run_persistence_service import persist_workflow_result


def build_workflow_result(
    *,
    workflow_run_id: str,
    workflow_name: str,
    workflow_status: str,
    simulation: bool,
    plan: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    execution_order = plan.get("execution_order", [])
    ordered = [step_runs[step_id] for step_id in execution_order if step_id in step_runs]
    remaining = [run for step_id, run in step_runs.items() if step_id not in set(execution_order)]
    all_step_runs = ordered + remaining
    completed = len([run for run in all_step_runs if run.get("status") == "completed"])
    blocked = len([run for run in all_step_runs if run.get("status") == "blocked"])
    failed = len([run for run in all_step_runs if run.get("status") == "failed"])
    return {
        "success": workflow_status == "completed",
        "workflow_run_id": workflow_run_id,
        "workflow_name": workflow_name,
        "status": workflow_status,
        "simulation": simulation,
        "plan_status": plan.get("status"),
        "step_count": len(all_step_runs),
        "completed_step_count": completed,
        "blocked_step_count": blocked,
        "failed_step_count": failed,
        "missing_capabilities": plan.get("missing_capabilities", []),
        "dependency_repair_plan": plan.get("dependency_repair_plan", []),
        "step_runs": all_step_runs,
    }


def finalize_result(
    db: Session,
    result: Dict[str, Any],
    *,
    log_event: bool,
    persist_result: bool,
) -> None:
    if persist_result:
        result["persistence"] = persist_workflow_result(db, result=result)
    if not log_event:
        return
    log_workflow_event(
        db,
        status=result["status"],
        metadata={
            "workflow_run_id": result["workflow_run_id"],
            "workflow_name": result["workflow_name"],
            "simulation": result["simulation"],
            "step_count": result["step_count"],
            "completed_step_count": result["completed_step_count"],
            "blocked_step_count": result["blocked_step_count"],
            "failed_step_count": result["failed_step_count"],
            "plan_status": result["plan_status"],
            "persisted": bool(result.get("persistence", {}).get("persisted")),
            "max_workflow_steps": MAX_WORKFLOW_STEPS,
            "max_step_dependencies": MAX_STEP_DEPENDENCIES,
            "max_context_json_bytes": MAX_CONTEXT_JSON_BYTES,
            "max_handler_result_json_bytes": MAX_HANDLER_RESULT_JSON_BYTES,
        },
    )
