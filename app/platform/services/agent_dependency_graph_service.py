from __future__ import annotations

import json
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from app.platform.agents.registry import list_agents
from app.platform.persistence.models import PlatformAgentDefinition, PlatformAuditEvent


DEFAULT_PLATFORM_REQUIRED_CAPABILITIES = [
    "orchestrator_task",
    "architect_task",
    "builder_task",
    "reviewer_task",
    "test_task",
    "agent_factory_task",
]


def _safe_json_loads(raw_value: str, default: Any) -> Any:
    try:
        return json.loads(raw_value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def _normalise_capabilities(raw_capabilities: Any) -> List[str]:
    if not isinstance(raw_capabilities, list):
        return []

    clean: List[str] = []
    for item in raw_capabilities:
        value = str(item).strip()
        if value and value not in clean:
            clean.append(value)

    return clean


def _log_dependency_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="agent_dependency_graph_check",
        actor_type="system",
        actor_id="agent_dependency_graph_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()


def build_agent_dependency_graph(
    db: Session,
    *,
    required_capabilities: List[str] | None = None,
    log_event: bool = True,
) -> Dict[str, Any]:
    required = required_capabilities or DEFAULT_PLATFORM_REQUIRED_CAPABILITIES

    registry_agents = list_agents()
    persisted_agents = (
        db.query(PlatformAgentDefinition)
        .filter(PlatformAgentDefinition.status == "active")
        .all()
    )

    capability_to_agents: Dict[str, List[str]] = {}
    agent_to_capabilities: Dict[str, List[str]] = {}
    persisted_agent_to_capabilities: Dict[str, List[str]] = {}

    for agent in registry_agents:
        agent_id = str(agent.get("agent_id") or "").strip()
        capabilities = _normalise_capabilities(agent.get("capabilities"))

        if not agent_id:
            continue

        agent_to_capabilities[agent_id] = capabilities

        for capability in capabilities:
            capability_to_agents.setdefault(capability, [])
            if agent_id not in capability_to_agents[capability]:
                capability_to_agents[capability].append(agent_id)

    for persisted_agent in persisted_agents:
        capabilities = _normalise_capabilities(
            _safe_json_loads(persisted_agent.capabilities_json, [])
        )
        persisted_agent_to_capabilities[persisted_agent.agent_id] = capabilities

        for capability in capabilities:
            capability_to_agents.setdefault(capability, [])
            if persisted_agent.agent_id not in capability_to_agents[capability]:
                capability_to_agents[capability].append(persisted_agent.agent_id)

    provided_capabilities: Set[str] = set(capability_to_agents.keys())
    required_set: Set[str] = set(required)

    missing_capabilities = sorted(required_set - provided_capabilities)

    duplicate_capability_providers = {
        capability: sorted(set(agent_ids))
        for capability, agent_ids in capability_to_agents.items()
        if len(set(agent_ids)) > 1
    }

    orphan_persisted_agents = []
    for persisted_agent in persisted_agents:
        if persisted_agent.agent_id not in agent_to_capabilities:
            orphan_persisted_agents.append(
                {
                    "agent_id": persisted_agent.agent_id,
                    "name": persisted_agent.name,
                    "capabilities": persisted_agent_to_capabilities.get(
                        persisted_agent.agent_id,
                        [],
                    ),
                    "impact": "Persisted agent exists in DB but is not currently loaded in memory.",
                }
            )

    repair_plan = []

    for missing_capability in missing_capabilities:
        repair_plan.append(
            {
                "type": "missing_required_capability",
                "capability": missing_capability,
                "recommended_action": "Use Agent Factory to propose or restore a specialist that provides this capability.",
                "requires_approval": True,
            }
        )

    for orphan_agent in orphan_persisted_agents:
        repair_plan.append(
            {
                "type": "orphan_persisted_agent",
                "agent_id": orphan_agent["agent_id"],
                "capabilities": orphan_agent["capabilities"],
                "recommended_action": "Run registry health repair to reload this persisted agent into memory.",
                "requires_approval": False,
            }
        )

    status = "healthy"
    if missing_capabilities:
        status = "missing_required_capabilities"
    elif duplicate_capability_providers:
        status = "duplicate_capability_providers"
    elif orphan_persisted_agents:
        status = "orphan_persisted_agents"

    result = {
        "success": status in {
            "healthy",
            "duplicate_capability_providers",
            "orphan_persisted_agents",
        },
        "status": status,
        "required_capabilities": sorted(required_set),
        "provided_capabilities": sorted(provided_capabilities),
        "missing_capabilities": missing_capabilities,
        "missing_capability_count": len(missing_capabilities),
        "duplicate_capability_providers": duplicate_capability_providers,
        "duplicate_capability_count": len(duplicate_capability_providers),
        "orphan_persisted_agents": orphan_persisted_agents,
        "orphan_persisted_agent_count": len(orphan_persisted_agents),
        "registry_agent_count": len(registry_agents),
        "persisted_agent_count": len(persisted_agents),
        "agent_to_capabilities": agent_to_capabilities,
        "capability_to_agents": {
            key: sorted(set(value))
            for key, value in capability_to_agents.items()
        },
        "repair_plan": repair_plan,
        "repair_plan_count": len(repair_plan),
    }

    if log_event:
        _log_dependency_event(
            db,
            status=status,
            metadata={
                "missing_capability_count": result["missing_capability_count"],
                "duplicate_capability_count": result["duplicate_capability_count"],
                "orphan_persisted_agent_count": result["orphan_persisted_agent_count"],
                "registry_agent_count": result["registry_agent_count"],
                "persisted_agent_count": result["persisted_agent_count"],
                "repair_plan_count": result["repair_plan_count"],
            },
        )

    return result
