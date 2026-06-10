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
