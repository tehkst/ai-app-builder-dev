from __future__ import annotations

import uuid
from typing import Any, Dict, List

from app.platform.services.agent_workflow_limits import MAX_STEP_DEPENDENCIES, MAX_WORKFLOW_STEPS


def validate_workflow_scalability(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    if len(steps) > MAX_WORKFLOW_STEPS:
        violations.append(
            {
                "reason": "max_workflow_steps_exceeded",
                "step_count": len(steps),
                "max_workflow_steps": MAX_WORKFLOW_STEPS,
            }
        )
    for step in steps:
        requires_steps = step.get("requires_steps") or []
        if len(requires_steps) > MAX_STEP_DEPENDENCIES:
            violations.append(
                {
                    "reason": "max_step_dependencies_exceeded",
                    "step_id": step.get("step_id"),
                    "dependency_count": len(requires_steps),
                    "max_step_dependencies": MAX_STEP_DEPENDENCIES,
                }
            )
    return violations


def build_blocked_scalability_result(
    *,
    workflow_run_id: str,
    workflow_name: str,
    simulation: bool,
    steps: List[Dict[str, Any]],
    violations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    step_runs = [_blocked_step_run(step, violations) for step in steps]
    return {
        "success": False,
        "workflow_run_id": workflow_run_id,
        "workflow_name": workflow_name,
        "status": "blocked",
        "simulation": simulation,
        "plan_status": "workflow_scalability_guardrail_violation",
        "step_count": len(step_runs),
        "completed_step_count": 0,
        "blocked_step_count": len(step_runs),
        "failed_step_count": 0,
        "missing_capabilities": [],
        "dependency_repair_plan": [],
        "scalability_violations": violations,
        "step_runs": step_runs,
    }


def _blocked_step_run(step: Dict[str, Any], violations: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "step_run_id": f"step_run_{uuid.uuid4().hex}",
        "step_id": step.get("step_id"),
        "title": step.get("title") or step.get("step_id") or "Untitled Step",
        "required_capability": step.get("required_capability"),
        "requires_steps": step.get("requires_steps") or [],
        "candidate_agents": [],
        "agent_available": False,
        "selected_agent": None,
        "status": "blocked",
        "output": None,
        "error": {
            "reason": "workflow_scalability_guardrail_violation",
            "violations": violations,
        },
    }
