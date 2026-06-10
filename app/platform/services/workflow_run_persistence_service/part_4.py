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

def compact_workflow_run_summary(detail: Dict[str, Any]) -> Dict[str, Any]:
    if not detail.get("found"):
        return detail

    steps = []
    for step in detail.get("steps") or []:
        handler_result = step.get("handler_result") or {}
        steps.append(
            {
                "step_id": step.get("step_id"),
                "title": step.get("title"),
                "status": step.get("status"),
                "required_capability": step.get("required_capability"),
                "selected_agent_id": step.get("selected_agent_id"),
                "requires_steps": step.get("requires_steps") or [],
                "handler_success": handler_result.get("success")
                if isinstance(handler_result, dict)
                else None,
                "handler_message": handler_result.get("message")
                if isinstance(handler_result, dict)
                else None,
            }
        )

    return {
        "success": detail.get("success"),
        "found": detail.get("found"),
        "summary": True,
        "workflow_run_id": detail.get("workflow_run_id"),
        "workflow_name": detail.get("workflow_name"),
        "status": detail.get("status"),
        "plan_status": detail.get("plan_status"),
        "simulation": detail.get("simulation"),
        "step_count": detail.get("step_count"),
        "completed_step_count": detail.get("completed_step_count"),
        "blocked_step_count": detail.get("blocked_step_count"),
        "failed_step_count": detail.get("failed_step_count"),
        "missing_capability_count": len(detail.get("missing_capabilities") or []),
        "dependency_repair_count": len(detail.get("dependency_repair_plan") or []),
        "created_at": detail.get("created_at"),
        "completed_at": detail.get("completed_at"),
        "steps": steps,
    }
