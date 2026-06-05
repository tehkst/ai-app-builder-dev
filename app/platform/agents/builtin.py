from __future__ import annotations

from typing import Any, Dict

from app.platform.agents.registry import AgentDefinition, register_agent


def test_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": True,
        "agent_id": "test_agent",
        "message": "Test agent executed task successfully.",
        "task_id": task.get("task_id"),
        "task_type": task.get("task_type"),
        "input_payload": task.get("input_payload", {}),
    }


def orchestrator_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    input_payload = task.get("input_payload", {})
    goal = input_payload.get("goal") or task.get("description") or task.get("title")

    return {
        "success": True,
        "agent_id": "orchestrator_agent",
        "message": "Orchestrator Agent V1 analyzed the task.",
        "goal": goal,
        "recommended_next_steps": [
            "Create an architecture planning task",
            "Create a builder implementation task",
            "Create a reviewer validation task",
            "Request approval before high-risk code or deployment changes",
        ],
        "child_task_creation": "planned_for_next_version",
    }


def register_builtin_agents() -> None:
    register_agent(
        AgentDefinition(
            agent_id="test_agent",
            name="Test Agent",
            description="Executes simple test tasks for validating the worker loop.",
            capabilities=["test_task", "worker_loop_test"],
            handler=test_agent_handler,
        )
    )

    register_agent(
        AgentDefinition(
            agent_id="orchestrator_agent",
            name="Orchestrator Agent",
            description="Plans and coordinates specialist agents for larger goals.",
            capabilities=["orchestrator_task", "plan_project", "agent_orchestration"],
            handler=orchestrator_agent_handler,
            requires_approval_for_new_tasks=True,
        )
    )


register_builtin_agents()
