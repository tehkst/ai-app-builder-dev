from __future__ import annotations

from typing import Any

from app.platform.agents.registry import AgentDefinition, register_agent


def mission_runtime_handler(task: dict[str, Any]) -> dict[str, Any]:
    from app.platform.operating_console.mission_run_service import execute_mission_task

    return execute_mission_task(task)


register_agent(
    AgentDefinition(
        agent_id="mission_runtime_agent",
        name="Durable Mission Runtime Agent",
        description="Continues one founder-approved mission preparation stage from persisted work.",
        capabilities=["approved_mission_stage"],
        handler=mission_runtime_handler,
    )
)
