# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.platform.persistence.models import (
    PlatformWorkflowRun,
    PlatformWorkflowStepRun,
    utc_now,
)

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
