# Split from the legacy module to keep each Python file under 200 lines.
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
