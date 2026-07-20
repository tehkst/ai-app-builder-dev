"""
Platform integration layer for the Native Coding Agent.

Connects the Native Coding Agent to existing platform components:
- Mission Pipeline routing
- Engineering Manager dispatch
- PlatformAgentTask execution
- Governance authorization

This is the bridge between the standalone coding_agent module and the
existing AI Software Factory platform services.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.policy import NATIVE_CODING_AGENT_ENABLED
from app.platform.coding_agent.service import CodingAgentService, start_coding_session


# ---------------------------------------------------------------------------
# Mission Pipeline integration
# ---------------------------------------------------------------------------

def route_mission_to_coding_agent(
    mission_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Route an eligible mission through the Native Coding Agent.

    Called by Mission Pipeline when:
    - NATIVE_CODING_AGENT_ENABLED is True
    - Mission has Engineering Manager breakdown with approved file scope
    - Mission has Architecture Decision
    - Mission has Repository Intelligence context

    Args:
        mission_payload: Full mission context including EM plan, arch decision, repo intel.

    Returns:
        Native Coding Agent execution result.
    """
    if not NATIVE_CODING_AGENT_ENABLED:
        return {
            "status": "native_coding_agent_disabled",
            "mission_id": str(mission_payload.get("mission_id", "unknown")),
            "next_step": "Use legacy code planner or enable NATIVE_CODING_AGENT_ENABLED.",
        }

    # Extract context from mission pipeline payload
    mission_id = str(mission_payload.get("mission_id") or "MISSION-UNSPECIFIED")
    workflow_run_id = str(mission_payload.get("workflow_run_id") or "WF-%s" % uuid.uuid4().hex[:8].upper())
    agent_task_id = str(mission_payload.get("agent_task_id") or "AGENT-TASK-%s" % uuid.uuid4().hex[:8].upper())

    em_plan = mission_payload.get("engineering_manager_plan") or {}
    arch_decision = mission_payload.get("architecture_decision") or {}
    repo_intel = mission_payload.get("repository_intelligence") or {}

    objective = str(
        em_plan.get("epic", {}).get("objective")
        or mission_payload.get("objective")
        or mission_payload.get("goal")
        or "Implement approved mission changes."
    )

    target_files = _extract_target_files(em_plan, arch_decision, repo_intel)

    # --- PlatformAgentTask: create BEFORE execution (Fix 3) ---
    _create_agent_task(
        agent_task_id=agent_task_id,
        mission_id=mission_id,
        task_type="coding_agent",
        status="claimed",
        workspace_id=None,  # Will be set after workspace creation
        input_payload={
            "mission_id": mission_id,
            "objective": objective,
            "target_files": target_files,
        },
    )

    # Create and execute the coding session
    service = CodingAgentService(
        mission_id=mission_id,
        workflow_run_id=workflow_run_id,
        agent_task_id=agent_task_id,
        objective=objective,
        target_files=target_files,
        repository=str(mission_payload.get("repository") or "").strip() or None,
        base_ref=str(mission_payload.get("base_ref") or "main"),
        owner_id=str(mission_payload.get("owner_id") or mission_payload.get("actor") or "").strip() or None,
        engineering_manager_plan=em_plan if em_plan else None,
        architecture_decision=arch_decision if arch_decision else None,
        model=mission_payload.get("model"),
        provider=mission_payload.get("provider"),
        max_iterations=int(mission_payload.get("max_iterations") or 0) or None,
        mission_validation_plan=mission_payload.get("mission_validation_plan") if isinstance(mission_payload.get("mission_validation_plan"), list) else None,
    )

    result = service.execute()

    # --- Transition PlatformAgentTask lifecycle based on result ---
    task_status = "completed" if result.get("status") == "verified_diff_ready" else "failed"
    _transition_agent_task(
        agent_task_id=agent_task_id,
        status=task_status,
        workspace_id=result.get("workspace_id"),
        result_payload={
            "status": result.get("status"),
            "iterations": result.get("iterations", 0),
            "workspace_id": result.get("workspace_id"),
            "verified_diff": result.get("verified_diff") is not None,
        },
    )

    # Add pipeline metadata
    result["pipeline_stage"] = "native_coding_agent_complete"
    result["pipeline_next_stage"] = "founder_review" if result.get("status") == "verified_diff_ready" else "blocked"

    return result


# ---------------------------------------------------------------------------
# Engineering Manager dispatch
# ---------------------------------------------------------------------------

def engineering_manager_dispatch_to_coding_agent(
    em_breakdown: Dict[str, Any],
    mission_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Engineering Manager dispatches approved breakdown to Native Coding Agent.

    Called after Engineering Manager produces a breakdown with:
    - engineering_tasks
    - validation_plan
    - dependency_order
    - acceptance_criteria

    Args:
        em_breakdown: Engineering Manager breakdown output.
        mission_context: Full mission context including arch decision, repo intel.

    Returns:
        Dispatch result with coding agent session reference.
    """
    if not NATIVE_CODING_AGENT_ENABLED:
        return {
            "status": "coding_agent_not_enabled",
            "fallback": "Use legacy patch application path.",
        }

    mission_id = str(em_breakdown.get("mission_id") or mission_context.get("mission_id") or "MISSION-UNSPECIFIED")
    agent_task_id = "AGENT-TASK-%s" % uuid.uuid4().hex[:8].upper()

    # Build dispatch payload from EM breakdown
    dispatch_payload = {
        "mission_id": mission_id,
        "workflow_run_id": str(mission_context.get("workflow_run_id") or "WF-%s" % uuid.uuid4().hex[:8].upper()),
        "agent_task_id": agent_task_id,
        "engineering_manager_plan": em_breakdown,
        "architecture_decision": mission_context.get("architecture_decision") or {},
        "repository_intelligence": mission_context.get("repository_intelligence") or {},
        "objective": em_breakdown.get("epic", {}).get("objective") or "Implement approved engineering breakdown.",
        "model": mission_context.get("model"),
        "provider": mission_context.get("provider"),
        "owner_id": mission_context.get("owner_id") or "EngineeringManager",
    }

    result = route_mission_to_coding_agent(dispatch_payload)

    return {
        "status": "dispatched_to_coding_agent",
        "mission_id": mission_id,
        "agent_task_id": agent_task_id,
        "coding_agent_result": result,
    }


# ---------------------------------------------------------------------------
# PlatformAgentTask lifecycle (Fix 3)
# ---------------------------------------------------------------------------

def _create_agent_task(
    agent_task_id: str,
    mission_id: str,
    task_type: str,
    status: str,
    workspace_id: Optional[str],
    input_payload: Dict[str, Any],
) -> None:
    """
    Create a PlatformAgentTask BEFORE execution starts.

    The task is the durable anchor for the coding session. It transitions
    through: claimed → running → completed | failed.
    Raises on persistence failure — no silent degradation.
    """
    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.execution_migrations import run_execution_layer_migrations
    from app.platform.persistence.models import PlatformAgentTask

    run_execution_layer_migrations()
    now = datetime.now(timezone.utc)

    task = PlatformAgentTask(
        task_id=agent_task_id,
        title="Native Coding Agent: %s" % mission_id,
        description="Coding session for mission %s" % mission_id,
        status=status,
        priority="normal",
        risk_level="low",
        task_type=task_type,
        requested_by="NativeCodingAgent",
        assigned_agent="NativeCodingAgent",
        workspace_id=workspace_id,
        input_payload_json=json.dumps(input_payload, sort_keys=True, default=str),
        result_payload_json="{}",
        approval_required=True,
        attempts=1,
        max_attempts=3,
        claimed_at=now,
        created_at=now,
        updated_at=now,
    )

    with PlatformSessionLocal() as db:
        db.add(task)
        db.commit()


def _transition_agent_task(
    agent_task_id: str,
    status: str,
    workspace_id: Optional[str],
    result_payload: Dict[str, Any],
) -> None:
    """
    Transition a PlatformAgentTask to its final state after execution.

    Updates status, workspace_id anchor, result payload, and timestamps.
    Raises on persistence failure.
    """
    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.execution_migrations import run_execution_layer_migrations
    from app.platform.persistence.models import PlatformAgentTask
    from sqlalchemy import update

    run_execution_layer_migrations()
    now = datetime.now(timezone.utc)

    values: Dict[str, Any] = {
        "status": status,
        "result_payload_json": json.dumps(result_payload, sort_keys=True, default=str),
        "updated_at": now,
    }

    if status in {"completed", "failed"}:
        values["completed_at"] = now
        values["failed_at"] = now if status == "failed" else None

    if workspace_id:
        values["workspace_id"] = workspace_id

    with PlatformSessionLocal() as db:
        result = db.execute(
            update(PlatformAgentTask)
            .where(PlatformAgentTask.task_id == agent_task_id)
            .values(**values)
        )
        db.commit()
        if result.rowcount != 1:
            raise RuntimeError(
                "Failed to transition agent task %s to status %s. "
                "Task record not found." % (agent_task_id, status)
            )


def get_coding_agent_task_status(agent_task_id: str) -> Dict[str, Any]:
    """
    Query the status of a coding agent task from PlatformAgentTask.

    Used for resumability and mission pipeline progress queries.
    """
    try:
        from app.platform.persistence.database import PlatformSessionLocal
        from app.platform.persistence.execution_migrations import run_execution_layer_migrations
        from app.platform.persistence.models import PlatformAgentTask

        run_execution_layer_migrations()
        with PlatformSessionLocal() as db:
            task = db.query(PlatformAgentTask).filter_by(task_id=agent_task_id).first()
            if not task:
                return {"status": "not-found", "agent_task_id": agent_task_id}
            return {
                "status": task.status,
                "agent_task_id": task.task_id,
                "mission_id": task.description,
                "result_payload": task.result_payload_json,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
    except Exception:
        return {"status": "unavailable", "agent_task_id": agent_task_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_target_files(
    em_plan: Dict[str, Any],
    arch_decision: Dict[str, Any],
    repo_intel: Dict[str, Any],
) -> List[str]:
    """Extract target file list from platform context."""
    # 1. Engineering Manager file plan
    file_plan = em_plan.get("file_plan") or em_plan.get("files") or em_plan.get("approved_files") or []
    if file_plan:
        files: List[str] = []
        for item in file_plan:
            if isinstance(item, str):
                files.append(item)
            elif isinstance(item, dict):
                path = item.get("path", "")
                if path:
                    files.append(path)
        if files:
            return files

    # 2. Architecture Decision required repository evidence
    arch_files = arch_decision.get("required_repository_evidence") or []
    if arch_files:
        return [item.get("path", "") for item in arch_files if item.get("path")]

    # 3. Repository Intelligence selected files
    selected = repo_intel.get("selected_files") or repo_intel.get("context_pack") or []
    if selected:
        result: List[str] = []
        for item in selected:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(item.get("path", ""))
        return [f for f in result if f]

    # Fallback
    return ["app/platform/server.py", "app/platform/api_contract.py"]
