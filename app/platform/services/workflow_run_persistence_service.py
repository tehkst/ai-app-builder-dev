from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.events.mission_lifecycle_publisher import publish_persisted_workflow_lifecycle
from app.platform.persistence.models import PlatformWorkflowRun, PlatformWorkflowStepRun, utc_now

TERMINAL_STATUSES = {"completed", "failed", "blocked", "skipped", "change_set_ready"}


def _json_dump(value: Any, fallback: Any) -> str:
    if value is None:
        value = fallback
    return json.dumps(value, sort_keys=True)


def _json_load(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _selected_agent_id(step_run: Dict[str, Any]) -> Optional[str]:
    selected_agent = step_run.get("selected_agent") or {}
    if isinstance(selected_agent, dict):
        return selected_agent.get("agent_id")
    return None


def _handler_result(step_run: Dict[str, Any]) -> Dict[str, Any]:
    output = step_run.get("output") or {}
    bridge_result = output.get("bridge_result") if isinstance(output, dict) else {}
    if isinstance(bridge_result, dict) and isinstance(bridge_result.get("handler_result"), dict):
        return bridge_result["handler_result"]
    return {}


def persist_workflow_result(db: Session, *, result: Dict[str, Any]) -> Dict[str, Any]:
    workflow_run_id = result.get("workflow_run_id")
    if not workflow_run_id:
        raise ValueError("workflow_run_id is required")

    completed_at = utc_now()
    workflow_run = (
        db.query(PlatformWorkflowRun)
        .filter(PlatformWorkflowRun.workflow_run_id == workflow_run_id)
        .first()
    )
    if not workflow_run:
        workflow_run = PlatformWorkflowRun(
            workflow_run_id=workflow_run_id,
            workflow_name=result.get("workflow_name") or "Agent Workflow",
            started_at=completed_at,
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
    workflow_run.missing_capabilities_json = _json_dump(result.get("missing_capabilities"), [])
    workflow_run.dependency_repair_plan_json = _json_dump(result.get("dependency_repair_plan"), [])
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    workflow_run.metadata_json = _json_dump({**metadata, "success": result.get("success")}, {})
    workflow_run.completed_at = completed_at if workflow_run.status in TERMINAL_STATUSES else None
    workflow_run.updated_at = completed_at

    persisted_steps = 0
    for step_run in result.get("step_runs") or []:
        step_run_id = step_run.get("step_run_id")
        if not step_run_id:
            continue
        persisted_step = (
            db.query(PlatformWorkflowStepRun)
            .filter(PlatformWorkflowStepRun.step_run_id == step_run_id)
            .first()
        )
        if not persisted_step:
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
        persisted_step.requires_steps_json = _json_dump(step_run.get("requires_steps"), [])
        persisted_step.candidate_agents_json = _json_dump(step_run.get("candidate_agents"), [])
        persisted_step.output_json = _json_dump(step_run.get("output"), {})
        persisted_step.error_json = _json_dump(step_run.get("error"), {})
        persisted_step.metadata_json = _json_dump(
            {
                "agent_available": step_run.get("agent_available"),
                "handler_result": _handler_result(step_run),
            },
            {},
        )
        persisted_step.updated_at = now
        if persisted_step.status in TERMINAL_STATUSES:
            persisted_step.completed_at = now
        persisted_steps += 1

    db.commit()
    publish_persisted_workflow_lifecycle(result)
    return {"workflow_run_id": workflow_run_id, "persisted": True, "persisted_step_count": persisted_steps}


def _step_to_dict(row: PlatformWorkflowStepRun) -> Dict[str, Any]:
    metadata = _json_load(row.metadata_json, {})
    output = _json_load(row.output_json, {})
    handler_result = metadata.get("handler_result") or {}
    if not handler_result:
        bridge_result = output.get("bridge_result") if isinstance(output, dict) else {}
        if isinstance(bridge_result, dict):
            handler_result = bridge_result.get("handler_result") or {}

    return {
        "step_run_id": row.step_run_id,
        "step_id": row.step_id,
        "title": row.title,
        "required_capability": row.required_capability,
        "selected_agent_id": row.selected_agent_id,
        "status": row.status,
        "requires_steps": _json_load(row.requires_steps_json, []),
        "candidate_agents": _json_load(row.candidate_agents_json, []),
        "output": output,
        "handler_result": handler_result,
        "error": _json_load(row.error_json, {}),
        "metadata": metadata,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_recent_workflow_runs(db: Session, *, limit: int = 10) -> List[Dict[str, Any]]:
    rows = (
        db.query(PlatformWorkflowRun)
        .order_by(PlatformWorkflowRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [compact_workflow_run_summary(_workflow_row_to_detail(db, row)) for row in rows]


def get_workflow_run_detail(db: Session, *, workflow_run_id: str) -> Dict[str, Any]:
    row = (
        db.query(PlatformWorkflowRun)
        .filter(PlatformWorkflowRun.workflow_run_id == workflow_run_id)
        .first()
    )
    if not row:
        return {"success": False, "found": False, "workflow_run_id": workflow_run_id, "steps": []}
    return _workflow_row_to_detail(db, row)


def _workflow_row_to_detail(db: Session, row: PlatformWorkflowRun) -> Dict[str, Any]:
    steps = (
        db.query(PlatformWorkflowStepRun)
        .filter(PlatformWorkflowStepRun.workflow_run_id == row.workflow_run_id)
        .order_by(PlatformWorkflowStepRun.created_at.asc())
        .all()
    )
    return {
        "success": True,
        "found": True,
        "workflow_run_id": row.workflow_run_id,
        "workflow_name": row.workflow_name,
        "status": row.status,
        "plan_status": row.plan_status,
        "simulation": row.simulation,
        "step_count": row.step_count,
        "completed_step_count": row.completed_step_count,
        "blocked_step_count": row.blocked_step_count,
        "failed_step_count": row.failed_step_count,
        "missing_capabilities": _json_load(row.missing_capabilities_json, []),
        "dependency_repair_plan": _json_load(row.dependency_repair_plan_json, []),
        "metadata": _json_load(row.metadata_json, {}),
        "steps": [_step_to_dict(step) for step in steps],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def compact_workflow_run_summary(detail: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": detail.get("success", False),
        "found": detail.get("found", False),
        "workflow_run_id": detail.get("workflow_run_id"),
        "workflow_name": detail.get("workflow_name"),
        "status": detail.get("status"),
        "plan_status": detail.get("plan_status"),
        "simulation": detail.get("simulation"),
        "step_count": detail.get("step_count", 0),
        "completed_step_count": detail.get("completed_step_count", 0),
        "blocked_step_count": detail.get("blocked_step_count", 0),
        "failed_step_count": detail.get("failed_step_count", 0),
        "missing_capabilities": detail.get("missing_capabilities", []),
        "generated_file_count": sum(
            len((step.get("handler_result") or {}).get("generated_files") or [])
            for step in detail.get("steps") or []
        ),
        "created_at": detail.get("created_at"),
        "completed_at": detail.get("completed_at"),
    }
