from __future__ import annotations

from typing import Any, Dict

from app.platform.agents.registry import AgentDefinition, register_agent
from app.platform.agents.factory import agent_factory_handler


def _goal(task: Dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    return str(input_payload.get("goal") or task.get("description") or task.get("title") or "No goal provided")


def architect_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success":