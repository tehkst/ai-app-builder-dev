from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.agents.registry import get_agent
from app.platform.services.agent_workflow_context import enforce_handler_result_limit


def execute_agent_via_bridge(
    db: Session,
    *,
    workflow_run_id: str,
    step_run: Dict[str, Any],
    workflow_context: Dict[str, Any],
    safe_mode: bool = True,
    log_event: bool = True,
) -> Dict[str, Any]:
    """Execute one registered specialist agent through the safe platform bridge.

    The bridge only invokes registered platform handlers. It does not execute generated
    code, write generated files to disk, deploy, or materialize previews.
    """

    del db, log_event

    selected_agent = step_run.get("selected_agent") or {}
    agent_id = selected_agent.get("agent_id") if isinstance(selected_agent, dict) else None
    if not agent_id:
        return {
            "success": False,
            "status": "missing_selected_agent",
            "workflow_run_id": workflow_run_id,
            "step_id": step_run.get("step_id"),
            "safe_mode": safe_mode,
        }

    agent = get_agent(str(agent_id))
    if not agent:
        return {
            "success": False,
            "status": "selected_agent_not_registered",
            "workflow_run_id": workflow_run_id,
            "step_id": step_run.get("step_id"),
            "agent_id": agent_id,
            "safe_mode": safe_mode,
        }

    task_payload = {
        "workflow_run_id": workflow_run_id,
        "step_run_id": step_run.get("step_run_id"),
        "step_id": step_run.get("step_id"),
        "title": step_run.get("title"),
        "description": step_run.get("description") or step_run.get("title"),
        "required_capability": step_run.get("required_capability"),
        "input_payload": {
            **(step_run.get("input") or {}),
            "workflow_context": workflow_context,
        },
        "safe_mode": safe_mode,
    }

    try:
        handler_result = agent.handler(task_payload)
        limited_result = enforce_handler_result_limit(handler_result)
        success = bool(handler_result.get("success")) if isinstance(handler_result, dict) else False
        return {
            "success": success,
            "status": "completed" if success else "handler_failed",
            "workflow_run_id": workflow_run_id,
            "step_id": step_run.get("step_id"),
            "agent_id": agent.agent_id,
            "handler_result": limited_result,
            "safe_mode": safe_mode,
            "safety_summary": {
                "generated_code_execution_performed": False,
                "filesystem_write_performed": False,
                "external_deployment_performed": False,
                "materialization_performed": False,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive production guardrail
        return {
            "success": False,
            "status": "handler_exception",
            "workflow_run_id": workflow_run_id,
            "step_id": step_run.get("step_id"),
            "agent_id": agent.agent_id,
            "error": str(exc),
            "safe_mode": safe_mode,
        }
