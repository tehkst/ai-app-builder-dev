from __future__ import annotations

from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from app.platform.agents.registry import list_agents


def _capability_index() -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = {}
    for agent in list_agents():
        for capability in agent.get("capabilities") or []:
            index.setdefault(str(capability), []).append(agent)
    return index


def _normalize_requires(step: Dict[str, Any]) -> List[str]:
    return [str(item) for item in (step.get("requires_steps") or []) if str(item).strip()]


def _execution_order(steps: List[Dict[str, Any]]) -> List[str]:
    by_id = {str(step.get("step_id")): step for step in steps if step.get("step_id")}
    ordered: List[str] = []
    temporary: Set[str] = set()
    permanent: Set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in permanent:
            return
        if step_id in temporary:
            return
        temporary.add(step_id)
        for dependency_id in _normalize_requires(by_id.get(step_id, {})):
            if dependency_id in by_id:
                visit(dependency_id)
        temporary.remove(step_id)
        permanent.add(step_id)
        ordered.append(step_id)

    for step in steps:
        step_id = step.get("step_id")
        if step_id:
            visit(str(step_id))
    return ordered


def _detect_cycle(steps: List[Dict[str, Any]]) -> bool:
    by_id = {str(step.get("step_id")): step for step in steps if step.get("step_id")}
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(step_id: str) -> bool:
        if step_id in visiting:
            return True
        if step_id in visited:
            return False
        visiting.add(step_id)
        for dependency_id in _normalize_requires(by_id.get(step_id, {})):
            if dependency_id in by_id and visit(dependency_id):
                return True
        visiting.remove(step_id)
        visited.add(step_id)
        return False

    return any(visit(step_id) for step_id in by_id)


def build_agent_execution_plan(
    db: Session,
    *,
    steps: List[Dict[str, Any]],
    log_event: bool = False,
) -> Dict[str, Any]:
    """Build a deterministic, capability-aware workflow execution plan.

    This planner is intentionally safe: it does not execute generated code, write files,
    deploy, or materialize anything. It only enriches planned steps with available
    agent candidates and dependency repair hints.
    """

    del db, log_event

    capability_to_agents = _capability_index()
    planned_steps: List[Dict[str, Any]] = []
    blocked_steps: List[Dict[str, Any]] = []
    missing_capabilities: List[str] = []
    validation_issues: List[Dict[str, Any]] = []

    seen_step_ids: Set[str] = set()
    for raw_step in steps:
        step = dict(raw_step)
        step_id = str(step.get("step_id") or "").strip()
        required_capability = str(step.get("required_capability") or "").strip()
        if not step_id:
            validation_issues.append({"reason": "missing_step_id", "step": raw_step})
            continue
        if step_id in seen_step_ids:
            validation_issues.append({"reason": "duplicate_step_id", "step_id": step_id})
            continue
        seen_step_ids.add(step_id)

        step["step_id"] = step_id
        step["requires_steps"] = _normalize_requires(step)
        candidates = capability_to_agents.get(required_capability, []) if required_capability else []
        step["candidate_agents"] = candidates
        step["agent_available"] = bool(candidates)

        if required_capability and not candidates:
            if required_capability not in missing_capabilities:
                missing_capabilities.append(required_capability)
            blocked_steps.append(step)
        planned_steps.append(step)

    known_ids = {step["step_id"] for step in planned_steps}
    for step in planned_steps:
        unknown_dependencies = [dep for dep in step.get("requires_steps") or [] if dep not in known_ids]
        if unknown_dependencies:
            validation_issues.append(
                {
                    "reason": "unknown_dependencies",
                    "step_id": step.get("step_id"),
                    "unknown_dependencies": unknown_dependencies,
                }
            )

    has_cycle = _detect_cycle(planned_steps)
    dependency_repair_plan = [
        {
            "missing_capability": capability,
            "recommended_action": "register_or_repair_specialist_agent",
            "approval_required": True,
        }
        for capability in missing_capabilities
    ]

    if validation_issues:
        status = "invalid"
    elif has_cycle:
        status = "blocked_dependency_cycle"
    elif missing_capabilities:
        status = "blocked_missing_capability"
    else:
        status = "ready"

    return {
        "success": status == "ready",
        "status": status,
        "steps": planned_steps,
        "blocked_steps": blocked_steps,
        "execution_order": _execution_order(planned_steps),
        "missing_capabilities": missing_capabilities,
        "dependency_repair_plan": dependency_repair_plan,
        "validation_issues": validation_issues,
        "has_cycle": has_cycle,
        "safety_summary": {
            "generated_code_execution_performed": False,
            "filesystem_write_performed": False,
            "external_deployment_performed": False,
            "materialization_performed": False,
        },
    }
