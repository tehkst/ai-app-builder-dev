# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.platform.agents.registry import get_agent
from app.platform.persistence.models import PlatformAuditEvent
SAFE_EXECUTION_AGENT_ALLOWLIST = {
    "test_agent",
    "orchestrator_agent",
    "architect_agent",
    "builder_agent",
    "backend_builder_agent",
    "database_builder_agent",
    "frontend_builder_agent",
    "reviewer_agent",
    "agent_factory_agent",
    # CEO/CTO/manager-tier agents: text-only decision-makers (build_management_agent_handler
    # never writes files, merges, or deploys - see generic_agent.SAFETY_BOUNDARY), added so a
    # real app build can actually route through the org-chart hierarchy end to end.
    "ceo_agent",
    "cto_agent",
    "engineering_manager_agent",
    "backend_manager_agent",
    "frontend_manager_agent",
    "database_manager_agent",
    "quality_manager_agent",
}

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


def _safe_task_payload(
    *,
    workflow_run_id: str,
    step_run: Dict[str, Any],
    workflow_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "task_id": f"bridge_task_{uuid.uuid4().hex}",
        "task_type": step_run.get("required_capability"),
        "title": step_run.get("title"),
        "description": step_run.get("description") or step_run.get("title"),
        "input_payload": {
            "workflow_run_id": workflow_run_id,
            "step_run_id": step_run.get("step_run_id"),
            "step_id": step_run.get("step_id"),
            "required_capability": step_run.get("required_capability"),
            "workflow_context": workflow_context or {},
        },
    }


def _log_bridge_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="agent_execution_bridge",
        actor_type="system",
        actor_id="agent_execution_bridge_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()
