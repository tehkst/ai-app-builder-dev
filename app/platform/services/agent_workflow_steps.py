from __future__ import annotations

import uuid
from typing import Any, Dict


def create_step_runs(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    step_runs: Dict[str, Dict[str, Any]] = {}
    combined_steps: Dict[str, Dict[str, Any]] = {}
    for step in plan.get("steps") or []:
        step_id = step.get("step_id")
        if step_id:
            combined_steps[step_id] = step
    for step in plan.get("blocked_steps") or []:
        step_id = step.get("step_id")
        if step_id and step_id not in combined_steps:
            combined_steps[step_id] = step
    for step_id, step in combined_steps.items():
        step_runs[step_id] = _new_step_run(step_id, step)
    return step_runs


def dependencies_completed(
    step_run: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
) -> bool:
    for required_step_id in step_run.get("requires_steps") or []:
        required_step = step_runs.get(required_step_id)
        if not required_step or required_step.get("status") != "completed":
            return False
    return True


def dependency_failed_or_blocked(
    step_run: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
) -> bool:
    for required_step_id in step_run.get("requires_steps") or []:
        required_step = step_runs.get(required_step_id)
        if not required_step or required_step.get("status") in {"failed", "blocked", "skipped", "escalated"}:
            return True
    return False


def select_agent_for_step(step_run: Dict[str, Any]) -> Dict[str, Any]:
    candidates = step_run.get("candidate_agents") or []
    selected_agent = candidates[0] if candidates else None
    step_run["selected_agent"] = selected_agent
    return step_run


def complete_step_simulation(step_run: Dict[str, Any]) -> Dict[str, Any]:
    select_agent_for_step(step_run)
    selected_agent = step_run.get("selected_agent")
    step_run["status"] = "completed"
    step_run["output"] = {
        "mode": "simulation",
        "message": f"Step '{step_run.get('step_id')}' completed in safe simulation mode.",
        "agent_id": selected_agent.get("agent_id") if selected_agent else None,
        "capability": step_run.get("required_capability"),
    }
    return step_run


def block_step(step_run: Dict[str, Any], *, reason: str) -> Dict[str, Any]:
    step_run["status"] = "blocked"
    step_run["error"] = {
        "reason": reason,
        "required_capability": step_run.get("required_capability"),
    }
    return step_run


def _new_step_run(step_id: str, step: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "step_run_id": f"step_run_{uuid.uuid4().hex}",
        "step_id": step_id,
        "title": step.get("title") or step_id,
        "description": step.get("description") or "",
        "input": step.get("input") or {},
        "required_capability": step.get("required_capability"),
        "requires_steps": step.get("requires_steps") or [],
        "candidate_agents": step.get("candidate_agents") or [],
        "agent_available": bool(step.get("agent_available")),
        "selected_agent": None,
        "status": "queued",
        "output": None,
        "error": None,
    }
