from __future__ import annotations

import json
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from app.platform.agents.registry import list_agents
from app.platform.persistence.models import PlatformAuditEvent
from app.platform.services.agent_dependency_graph_service import build_agent_dependency_graph


def _normalize_capability(value: str) -> str:
    return value.strip()


def _build_capability_index() -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = {}

    for agent_data in list_agents():
        for capability in agent_data.get("capabilities", []):
            normalized = _normalize_capability(capability)
            index.setdefault(normalized, []).append(agent_data)

    return index


def _topological_sort(
    steps_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    dependencies: Dict[str, Set[str]] = {}
    dependents: Dict[str, Set[str]] = {}
    known_step_ids = set(steps_by_id.keys())

    for step_id, step in steps_by_id.items():
        requires = {
            required_step_id
            for required_step_id in (step.get("requires_steps") or [])
            if required_step_id in known_step_ids
        }
        dependencies[step_id] = requires
        dependents.setdefault(step_id, set())

        for required_step_id in requires:
            dependents.setdefault(required_step_id, set()).add(step_id)

    ready = sorted(
        step_id
        for step_id, required_ids in dependencies.items()
        if not required_ids
    )

    execution_order: List[str] = []

    while ready:
        current = ready.pop(0)
        execution_order.append(current)

        for dependent in sorted(dependents.get(current, set())):
            dependencies[dependent].discard(current)
            if not dependencies[dependent] and dependent not in execution_order and dependent not in ready:
                ready.append(dependent)
                ready.sort()

    unresolved = {
        step_id: sorted(required_ids)
        for step_id, required_ids in dependencies.items()
        if required_ids
    }

    return {
        "has_cycle": bool(unresolved),
        "execution_order": execution_order,
        "unresolved_dependencies": unresolved,
    }


def _validate_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for index, step in enumerate(steps):
        step_id = str(step.get("step_id") or "").strip()
        capability = str(step.get("required_capability") or "").strip()

        if not step_id:
            issues.append(
                {
                    "index": index,
                    "issue": "missing_step_id",
                }
            )
            continue

        if step_id in seen:
            issues.append(
                {
                    "step_id": step_id,
                    "issue": "duplicate_step_id",
                }
            )

        seen.add(step_id)

        if not capability:
            issues.append(
                {
                    "step_id": step_id,
                    "issue": "missing_required_capability",
                }
            )

    valid_step_ids = {
        str(step.get("step_id") or "").strip()
        for step in steps
        if str(step.get("step_id") or "").strip()
    }

    for step in steps:
        step_id = str(step.get("step_id") or "").strip()
        for required_step_id in step.get("requires_steps") or []:
            if required_step_id not in valid_step_ids:
                issues.append(
                    {
                        "step_id": step_id,
                        "issue": "unknown_required_step",
                        "required_step_id": required_step_id,
                    }
                )

    return issues


def _step_to_plan_item(
    step: Dict[str, Any],
    *,
    capability_index: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    capability = _normalize_capability(str(step.get("required_capability") or ""))
    matching_agents = capability_index.get(capability, [])

    return {
        "step_id": step.get("step_id"),
        "title": step.get("title") or step.get("step_id"),
        "description": step.get("description") or "",
        "required_capability": capability,
        "requires_steps": step.get("requires_steps") or [],
        "agent_available": bool(matching_agents),
        "candidate_agents": [
            {
                "agent_id": agent.get("agent_id"),
                "name": agent.get("name"),
                "risk_level": agent.get("risk_level"),
                "safe_mode": agent.get("safe_mode"),
                "writes_code": agent.get("writes_code"),
            }
            for agent in matching_agents
        ],
    }


def _log_execution_plan_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="agent_execution_dependency_plan",
        actor_type="system",
        actor_id="agent_execution_planner_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()


def build_agent_execution_plan(
    db: Session,
    *,
    steps: List[Dict[str, Any]],
    log_event: bool = True,
) -> Dict[str, Any]:
    validation_issues = _validate_steps(steps)

    steps_by_id = {
        str(step.get("step_id") or "").strip(): step
        for step in steps
        if str(step.get("step_id") or "").strip()
    }

    topo = _topological_sort(steps_by_id)
    capability_index = _build_capability_index()

    planned_steps_by_id = {
        step_id: _step_to_plan_item(step, capability_index=capability_index)
        for step_id, step in steps_by_id.items()
    }

    ordered_steps = [
        planned_steps_by_id[step_id]
        for step_id in topo["execution_order"]
        if step_id in planned_steps_by_id
    ]

    blocked_steps = [
        planned_steps_by_id[step_id]
        for step_id, item in planned_steps_by_id.items()
        if not item["agent_available"]
    ]

    missing_capabilities = sorted(
        {
            item["required_capability"]
            for item in blocked_steps
            if item.get("required_capability")
        }
    )

    dependency_graph = build_agent_dependency_graph(
        db,
        required_capabilities=missing_capabilities,
        log_event=False,
    )

    status = "ready"
    if validation_issues:
        status = "invalid_plan"
    elif topo["has_cycle"]:
        status = "dependency_cycle_detected"
    elif missing_capabilities:
        status = "missing_required_capabilities"

    result = {
        "success": status == "ready",
        "status": status,
        "step_count": len(steps_by_id),
        "ordered_step_count": len(ordered_steps),
        "blocked_step_count": len(blocked_steps),
        "missing_capability_count": len(missing_capabilities),
        "steps": ordered_steps,
        "blocked_steps": blocked_steps,
        "missing_capabilities": missing_capabilities,
        "validation_issues": validation_issues,
        "has_cycle": topo["has_cycle"],
        "unresolved_dependencies": topo["unresolved_dependencies"],
        "execution_order": topo["execution_order"],
        "dependency_repair_plan": dependency_graph.get("repair_plan", []),
    }

    if log_event:
        _log_execution_plan_event(
            db,
            status=status,
            metadata={
                "step_count": result["step_count"],
                "ordered_step_count": result["ordered_step_count"],
                "blocked_step_count": result["blocked_step_count"],
                "missing_capability_count": result["missing_capability_count"],
                "has_cycle": result["has_cycle"],
            },
        )

    return result
