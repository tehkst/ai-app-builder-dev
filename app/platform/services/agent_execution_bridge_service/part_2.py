# Split from the legacy module to keep each Python file under 200 lines. The shared
# allowlist and helper functions (SAFE_EXECUTION_AGENT_ALLOWLIST, _safe_task_payload,
# _log_bridge_event) live in part_1.py and reach this module's namespace via the package
# __init__.py's merge - see that file's docstring for how the split-file convention works.
from __future__ import annotations
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.platform.agents.registry import get_agent


def execute_agent_via_bridge(
    db: Session,
    *,
    workflow_run_id: str,
    step_run: Dict[str, Any],
    workflow_context: Optional[Dict[str, Any]] = None,
    safe_mode: bool = True,
    log_event: bool = True,
) -> Dict[str, Any]:
    selected_agent = step_run.get("selected_agent") or {}
    agent_id = selected_agent.get("agent_id")

    if not agent_id:
        result = {
            "success": False,
            "status": "agent_not_selected",
            "agent_id": None,
            "step_id": step_run.get("step_id"),
            "error": "No selected agent was provided for this step.",
        }
        if log_event:
            _log_bridge_event(
                db,
                status="agent_not_selected",
                metadata={
                    "workflow_run_id": workflow_run_id,
                    "step_id": step_run.get("step_id"),
                    "required_capability": step_run.get("required_capability"),
                },
            )
        return result

    if safe_mode and agent_id not in SAFE_EXECUTION_AGENT_ALLOWLIST:
        result = {
            "success": False,
            "status": "agent_not_allowlisted",
            "agent_id": agent_id,
            "step_id": step_run.get("step_id"),
            "error": "Agent is not allowlisted for safe bridge execution.",
        }
        if log_event:
            _log_bridge_event(
                db,
                status="agent_not_allowlisted",
                metadata={
                    "workflow_run_id": workflow_run_id,
                    "step_id": step_run.get("step_id"),
                    "agent_id": agent_id,
                    "required_capability": step_run.get("required_capability"),
                },
            )
        return result

    agent = get_agent(agent_id)
    if not agent:
        result = {
            "success": False,
            "status": "agent_not_registered",
            "agent_id": agent_id,
            "step_id": step_run.get("step_id"),
            "error": "Selected agent is not registered in the active registry.",
        }
        if log_event:
            _log_bridge_event(
                db,
                status="agent_not_registered",
                metadata={
                    "workflow_run_id": workflow_run_id,
                    "step_id": step_run.get("step_id"),
                    "agent_id": agent_id,
                    "required_capability": step_run.get("required_capability"),
                },
            )
        return result

    required_capability = step_run.get("required_capability")
    if required_capability and required_capability not in agent.capabilities:
        result = {
            "success": False,
            "status": "capability_mismatch",
            "agent_id": agent_id,
            "step_id": step_run.get("step_id"),
            "error": "Selected agent does not provide the required capability.",
            "required_capability": required_capability,
            "agent_capabilities": list(agent.capabilities),
        }
        if log_event:
            _log_bridge_event(
                db,
                status="capability_mismatch",
                metadata={
                    "workflow_run_id": workflow_run_id,
                    "step_id": step_run.get("step_id"),
                    "agent_id": agent_id,
                    "required_capability": required_capability,
                    "agent_capabilities": list(agent.capabilities),
                },
            )
        return result

    task_payload = _safe_task_payload(
        workflow_run_id=workflow_run_id,
        step_run=step_run,
        workflow_context=workflow_context,
    )

    try:
        handler_result = agent.handler(task_payload)
    except Exception as exc:
        result = {
            "success": False,
            "status": "handler_exception",
            "agent_id": agent_id,
            "step_id": step_run.get("step_id"),
            "error": str(exc),
        }
        if log_event:
            _log_bridge_event(
                db,
                status="handler_exception",
                metadata={
                    "workflow_run_id": workflow_run_id,
                    "step_id": step_run.get("step_id"),
                    "agent_id": agent_id,
                    "error": str(exc),
                },
            )
        return result

    result = {
        "success": bool(handler_result.get("success")),
        "status": "completed" if handler_result.get("success") else "failed",
        "agent_id": agent_id,
        "step_id": step_run.get("step_id"),
        "safe_mode": safe_mode,
        "task_payload": task_payload,
        "handler_result": handler_result,
    }

    if log_event:
        _log_bridge_event(
            db,
            status=result["status"],
            metadata={
                "workflow_run_id": workflow_run_id,
                "step_id": step_run.get("step_id"),
                "agent_id": agent_id,
                "required_capability": required_capability,
                "safe_mode": safe_mode,
                "handler_success": result["success"],
            },
        )

    return result
