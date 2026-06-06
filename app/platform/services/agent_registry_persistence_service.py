from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.agents.registry import AgentDefinition, get_agent, register_agent
from app.platform.persistence.models import PlatformAgentDefinition


def _safe_persisted_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = (task or {}).get("goal") or (task or {}).get("input_payload", {}).get("goal")

    return {
        "success": True,
        "safe_mode": True,
        "writes_code": False,
        "agent_id": (task or {}).get("agent_id"),
        "message": "Persisted specialist agent executed in metadata-only safe mode.",
        "goal": goal,
        "next_step": "Future versions may add executable specialist handlers behind approval gates.",
    }


def _load_capabilities(agent: PlatformAgentDefinition) -> List[str]:
    try:
        capabilities = json.loads(agent.capabilities_json or "[]")
    except json.JSONDecodeError:
        return []

    if not isinstance(capabilities, list):
        return []

    return [str(item) for item in capabilities if str(item).strip()]


def load_persisted_agents_into_registry(db: Session) -> Dict[str, Any]:
    db_agents = (
        db.query(PlatformAgentDefinition)
        .filter(PlatformAgentDefinition.status == "active")
        .all()
    )

    loaded_agents: List[Dict[str, Any]] = []
    skipped_agents: List[Dict[str, Any]] = []

    for db_agent in db_agents:
        capabilities = _load_capabilities(db_agent)
        if not capabilities:
            skipped_agents.append(
                {
                    "agent_id": db_agent.agent_id,
                    "reason": "no_valid_capabilities",
                }
            )
            continue

        if get_agent(db_agent.agent_id):
            skipped_agents.append(
                {
                    "agent_id": db_agent.agent_id,
                    "reason": "already_in_registry",
                }
            )
            continue

        def handler(task: Dict[str, Any], agent_id: str = db_agent.agent_id) -> Dict[str, Any]:
            task = dict(task or {})
            task.setdefault("agent_id", agent_id)
            return _safe_persisted_agent_handler(task)

        register_agent(
            AgentDefinition(
                agent_id=db_agent.agent_id,
                name=db_agent.name,
                description=db_agent.description,
                capabilities=capabilities,
                handler=handler,
                requires_approval_for_new_tasks=True,
            )
        )

        loaded_agents.append(
            {
                "agent_id": db_agent.agent_id,
                "name": db_agent.name,
                "capabilities": capabilities,
                "safe_mode": db_agent.safe_mode,
                "writes_code": db_agent.writes_code,
            }
        )

    return {
        "success": True,
        "db_agent_count": len(db_agents),
        "loaded_count": len(loaded_agents),
        "skipped_count": len(skipped_agents),
        "loaded_agents": loaded_agents,
        "skipped_agents": skipped_agents,
    }
