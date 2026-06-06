from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.agents.registry import get_agent, list_agents
from app.platform.persistence.models import PlatformAgentDefinition, PlatformAuditEvent
from app.platform.services.agent_registry_persistence_service import (
    load_persisted_agents_into_registry,
)


def _safe_json_loads(raw_value: str, default: Any) -> Any:
    try:
        return json.loads(raw_value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def _log_registry_health_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="agent_registry_health_check",
        actor_type="system",
        actor_id="agent_registry_health_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()


def check_and_repair_agent_registry(
    db: Session,
    *,
    repair: bool = True,
    log_event: bool = True,
) -> Dict[str, Any]:
    persisted_agents = (
        db.query(PlatformAgentDefinition)
        .filter(PlatformAgentDefinition.status == "active")
        .all()
    )

    registry_agents = list_agents()
    registry_agent_ids = {agent["agent_id"] for agent in registry_agents}

    missing_agents: List[Dict[str, Any]] = []
    invalid_agents: List[Dict[str, Any]] = []
    duplicate_capabilities: Dict[str, List[str]] = {}

    capability_owner_map: Dict[str, List[str]] = {}

    for db_agent in persisted_agents:
        capabilities = _safe_json_loads(db_agent.capabilities_json, [])

        if not isinstance(capabilities, list) or not capabilities:
            invalid_agents.append(
                {
                    "agent_id": db_agent.agent_id,
                    "reason": "invalid_or_empty_capabilities",
                }
            )
            continue

        clean_capabilities = [
            str(item).strip()
            for item in capabilities
            if str(item).strip()
        ]

        if not clean_capabilities:
            invalid_agents.append(
                {
                    "agent_id": db_agent.agent_id,
                    "reason": "no_clean_capabilities",
                }
            )
            continue

        if db_agent.agent_id not in registry_agent_ids:
            missing_agents.append(
                {
                    "agent_id": db_agent.agent_id,
                    "name": db_agent.name,
                    "capabilities": clean_capabilities,
                }
            )

        for capability in clean_capabilities:
            capability_owner_map.setdefault(capability, []).append(db_agent.agent_id)

    for capability, owners in capability_owner_map.items():
        unique_owners = sorted(set(owners))
        if len(unique_owners) > 1:
            duplicate_capabilities[capability] = unique_owners

    repair_result: Dict[str, Any] = {
        "repair_attempted": False,
        "repair_success": None,
        "loaded_count": 0,
        "skipped_count": 0,
    }

    if repair and missing_agents:
        repair_result = load_persisted_agents_into_registry(db)
        repair_result["repair_attempted"] = True
        repair_result["repair_success"] = bool(repair_result.get("success"))

    registry_agents_after_repair = list_agents()

    status = "healthy"
    if invalid_agents or duplicate_capabilities:
        status = "needs_attention"
    elif missing_agents and repair_result.get("repair_success") is False:
        status = "repair_failed"
    elif missing_agents and repair_result.get("repair_success") is True:
        status = "repaired"
    elif missing_agents:
        status = "missing_agents"

    result = {
        "success": status in {"healthy", "repaired", "needs_attention"},
        "status": status,
        "repair_enabled": repair,
        "persisted_agent_count": len(persisted_agents),
        "registry_agent_count_before": len(registry_agents),
        "registry_agent_count_after": len(registry_agents_after_repair),
        "missing_count": len(missing_agents),
        "invalid_count": len(invalid_agents),
        "duplicate_capability_count": len(duplicate_capabilities),
        "missing_agents": missing_agents,
        "invalid_agents": invalid_agents,
        "duplicate_capabilities": duplicate_capabilities,
        "repair_result": repair_result,
        "registered_registry_agents": registry_agents_after_repair,
    }

    if log_event:
        _log_registry_health_event(
            db,
            status=status,
            metadata={
                "persisted_agent_count": result["persisted_agent_count"],
                "registry_agent_count_before": result["registry_agent_count_before"],
                "registry_agent_count_after": result["registry_agent_count_after"],
                "missing_count": result["missing_count"],
                "invalid_count": result["invalid_count"],
                "duplicate_capability_count": result["duplicate_capability_count"],
                "repair_enabled": repair,
            },
        )

    return result
