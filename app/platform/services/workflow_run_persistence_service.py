from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import (
    PlatformWorkflowRun,
    PlatformWorkflowStepRun,
    utc_now,
)


def _json_dump(value: Any, fallback: Any) -> str:
    if value is None:
        value = fallback
    return json.dumps(value, sort_keys=True)


def _selected_agent_id(step_run: Dict[str, Any]) -> Optional[str]:
    selected_agent = step_run.get("selected_agent") or {}
    if isinstance(selected_agent, dict):
        return selected_agent.get("agent_id")
    return None


def persist_workflow_result(
    db: Session,
    *,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    workflow_run_id = result.get("workflow_run_id")
    if not workflow_run_id:
        raise ValueError("workflow_run_id is required")

    existing_run = (
        db.query(PlatformWorkflowRun)
        .filter(PlatformWorkflowRun.workflow_run_id == workflow_run_id)
        .first()
    )

    completed_at = utc_now()

    if existing_run:
        workflow_run = existing_run
    else:
        workflow_run = PlatformWorkflowRun(
            workflow_run_id=workflow_run_id,
            workflow_name=result.get("workflow_name") or "Agent Workflow",
        )
        db.add(workflow_run)

    workflow_run.workflow_name = result.get("workflow_name") or workflow_run.workflow_name
    workflow_run.status = result.get("status") or "unknown"
    workflow_run.plan_status = result.get("plan_status")
    workflow_run.simulation = bool(result.get("simulation"))
    workflow_run.step_count = int(result.get("step_count") or 0)
    workflow_run.completed_step_count = int(result.get("completed_step_count") or 0)
    workflow_run.blocked_step_count = int(result.get("blocked_step_count") or 0)
    workflow_run.failed_step_count = int(result.get("failed_step_count") or 0)
    workflow_run.missing_capabilities_json = _json_dump(
        result.get("missing_capabilities"),
        [],
    )
    workflow_run.dependency_repair_plan_json = _json_dump(
        result.get("dependency_repair_plan"),
        [],
    )
    workflow_run.metadata_json = _json_dump(
        {
            "success": result.get("success"),
        },
        {},
    )
    workflow_run.completed_at = completed_at
    workflow_run.updated_at = completed_at

    persisted_steps = 0

    for step_run in result.get("step_runs") or []:
        step_run_id = step_run.get("step_run_id")
        if not step_run_id:
            continue

        existing_step = (
            db.query(PlatformWorkflowStepRun)
            .filter(PlatformWorkflowStepRun.step_run_id == step_run_id)
            .first()
        )

        if existing_step:
            persisted_step = existing_step
        else:
            persisted_step = PlatformWorkflowStepRun(
                workflow_run_id=workflow_run_id,
                step_run_id=step_run_id,
                step_id=step_run.get("step_id") or "unknown",
                title=step_run.get("title") or step_run.get("step_id") or "Untitled Step",
            )
            db.add(persisted_step)

        now = utc_now()

        persisted_step.workflow_run_id = workflow_run_id
        persisted_step.step_id = step_run.get("step_id") or persisted_step.step_id
        persisted_step.title = step_run.get("title") or persisted_step.title
        persisted_step.required_capability = step_run.get("required_capability")
        persisted_step.selected_agent_id = _selected_agent_id(step_run)
        persisted_step.status = step_run.get("status") or "unknown"
        persisted_step.requires_steps_json = _json_dump(
            step_run.get("requires_steps"),
            [],
        )
        persisted_step.candidate_agents_json = _json_dump(
            step_run.get("candidate_agents"),
            [],
        )
        persisted_step.output_json = _json_dump(
            step_run.get("output"),
            {},
        )
        persisted_step.error_json = _json_dump(
            step_run.get("error"),
            {},
        )
        persisted_step.metadata_json = _json_dump(
            {
                "agent_available": step_run.get("agent_available"),
                "workflow_context": step_run.get("workflow_context"),
            },
            {},
        )
        persisted_step.updated_at = now

        if persisted_step.status in {"completed", "failed", "blocked", "skipped"}:
            persisted_step.completed_at = now

        persisted_steps += 1

    db.commit()

    return {
        "workflow_run_id": workflow_run_id,
        "persisted": True,
        "persisted_step_count": persisted_steps,
    }


def list_recent_workflow_runs(
    db: Session,
    *,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    rows = (
        db.query(PlatformWorkflowRun)
        .order_by(PlatformWorkflowRun.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "workflow_run_id": row.workflow_run_id,
            "workflow_name": row.workflow_name,
            "status": row.status,
            "plan_status": row.plan_status,
            "simulation": row.simulation,
            "step_count": row.step_count,
            "completed_step_count": row.completed_step_count,
            "blocked_step_count": row.blocked_step_count,
            "failed_step_count": row.failed_step_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in rows
    ]


def _json_load(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def get_workflow_run_detail(
    db: Session,
    *,
    workflow_run_id: str,
) -> Dict[str, Any]:
    workflow_run_id = (workflow_run_id or "").strip()
    if not workflow_run_id:
        raise ValueError("workflow_run_id is required")

    run = (
        db.query(PlatformWorkflowRun)
        .filter(PlatformWorkflowRun.workflow_run_id == workflow_run_id)
        .first()
    )

    if not run:
        return {
            "success": False,
            "found": False,
            "workflow_run_id": workflow_run_id,
            "error": "workflow_run_not_found",
        }

    step_rows = (
        db.query(PlatformWorkflowStepRun)
        .filter(PlatformWorkflowStepRun.workflow_run_id == workflow_run_id)
        .order_by(PlatformWorkflowStepRun.created_at.asc())
        .all()
    )

    steps = []
    for step in step_rows:
        output = _json_load(step.output_json, {})
        metadata = _json_load(step.metadata_json, {})
        error = _json_load(step.error_json, {})

        bridge_result = {}
        if isinstance(output, dict):
            bridge_result = output.get("bridge_result") or {}

        handler_result = {}
        if isinstance(bridge_result, dict):
            handler_result = bridge_result.get("handler_result") or {}

        steps.append(
            {
                "step_run_id": step.step_run_id,
                "step_id": step.step_id,
                "title": step.title,
                "required_capability": step.required_capability,
                "selected_agent_id": step.selected_agent_id,
                "status": step.status,
                "requires_steps": _json_load(step.requires_steps_json, []),
                "candidate_agents": _json_load(step.candidate_agents_json, []),
                "error": error,
                "handler_result": handler_result,
                "workflow_context": metadata.get("workflow_context")
                if isinstance(metadata, dict)
                else None,
                "created_at": step.created_at.isoformat() if step.created_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            }
        )

    metadata = _json_load(run.metadata_json, {})

    return {
        "success": True,
        "found": True,
        "workflow_run_id": run.workflow_run_id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "plan_status": run.plan_status,
        "simulation": run.simulation,
        "step_count": run.step_count,
        "completed_step_count": run.completed_step_count,
        "blocked_step_count": run.blocked_step_count,
        "failed_step_count": run.failed_step_count,
        "missing_capabilities": _json_load(run.missing_capabilities_json, []),
        "dependency_repair_plan": _json_load(run.dependency_repair_plan_json, []),
        "metadata": metadata,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "steps": steps,
    }
