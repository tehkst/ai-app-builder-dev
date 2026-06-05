from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


AgentHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    handler: AgentHandler
    requires_approval_for_new_tasks: bool = False


_AGENT_REGISTRY: Dict[str, AgentDefinition] = {}


def register_agent(agent: AgentDefinition) -> None:
    if not agent.agent_id or not agent.agent_id.strip():
        raise ValueError("agent_id is required")
    _AGENT_REGISTRY[agent.agent_id] = agent


def get_agent(agent_id: str) -> Optional[AgentDefinition]:
    return _AGENT_REGISTRY.get(agent_id)


def list_agents() -> List[Dict[str, Any]]:
    return [
        {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "capabilities": agent.capabilities,
            "requires_approval_for_new_tasks": agent.requires_approval_for_new_tasks,
        }
        for agent in sorted(_AGENT_REGISTRY.values(), key=lambda item: item.agent_id)
    ]


def choose_agent_for_task(task_type: str) -> Optional[AgentDefinition]:
    for agent in _AGENT_REGISTRY.values():
        if task_type in agent.capabilities:
            return agent
    return None
