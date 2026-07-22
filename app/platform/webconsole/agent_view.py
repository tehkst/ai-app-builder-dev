from __future__ import annotations

from typing import Any, Dict, Iterable

from app.platform.services.board_room_agents import BOARD_ROOM_AGENTS
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def agent_view(
    agent_count: int | None = None,
    capability_count: int | None = None,
    *,
    runtime_status: Dict[str, Dict[str, Any]] | None = None,
    current_assignments: Dict[str, Dict[str, Any]] | None = None,
) -> ConsoleView:
    """Render the existing multi-agent system in the existing admin console.

    AFOS-001 deliberately projects established agent definitions and runtime/task
    read models. It does not create or own an agent registry, runtime store, task
    model, orchestration layer, or persistence boundary.
    """

    agents = list(BOARD_ROOM_AGENTS)
    runtime_status = runtime_status or {}
    current_assignments = current_assignments or {}

    resolved_agent_count = len(agents) if agent_count is None else agent_count
    resolved_capability_count = (
        _capability_count(agents) if capability_count is None else capability_count
    )

    cards = [
        ConsoleCard(
            "agent_count",
            "Agents",
            str(resolved_agent_count),
            "active",
            {"source": "BOARD_ROOM_AGENTS", "owns_registry": False},
        ),
        ConsoleCard(
            "agent_capabilities",
            "Capabilities",
            str(resolved_capability_count),
            "active",
            {"source": "existing_agent_definitions"},
        ),
    ]

    for agent in agents:
        runtime = runtime_status.get(agent.key) or {}
        assignment = current_assignments.get(agent.key) or {}
        status = str(runtime.get("status") or "available")
        health = str(runtime.get("health") or _health_from_status(status))
        current_mission = assignment.get("mission_id")
        current_task = assignment.get("task") or assignment.get("task_id")

        cards.append(
            ConsoleCard(
                card_id=f"agent_{agent.key}",
                title=agent.title,
                value=status,
                status=health,
                metadata={
                    "agent_key": agent.key,
                    "mandate": agent.mandate,
                    "skills": _skills(agent.lens),
                    "current_mission": current_mission,
                    "current_task": current_task,
                    "last_seen": runtime.get("last_seen"),
                    "runtime_source": runtime.get("source") or "existing_runtime_read_model",
                    "task_source": assignment.get("source") or "existing_agent_task_lifecycle",
                    "owns_state": False,
                },
            )
        )

    return ConsoleView("agent_view", "Agent Center", cards)


def agent_detail(
    agent_key: str,
    *,
    runtime_status: Dict[str, Dict[str, Any]] | None = None,
    current_assignments: Dict[str, Dict[str, Any]] | None = None,
) -> ConsoleView:
    """Return a focused details view for one existing agent."""

    runtime_status = runtime_status or {}
    current_assignments = current_assignments or {}
    agent = next((item for item in BOARD_ROOM_AGENTS if item.key == agent_key), None)
    if agent is None:
        return ConsoleView(
            "agent_detail",
            "Agent Details",
            [ConsoleCard("agent_not_found", "Agent", agent_key, "degraded", {})],
        )

    runtime = runtime_status.get(agent.key) or {}
    assignment = current_assignments.get(agent.key) or {}
    status = str(runtime.get("status") or "available")

    cards = [
        ConsoleCard(
            "identity",
            agent.title,
            agent.key,
            _health_from_status(status),
            {"mandate": agent.mandate},
        ),
        ConsoleCard(
            "skills",
            "Skills & Capabilities",
            str(len(_skills(agent.lens))),
            "active",
            {"skills": _skills(agent.lens)},
        ),
        ConsoleCard(
            "runtime",
            "Live Runtime Status",
            status,
            str(runtime.get("health") or _health_from_status(status)),
            dict(runtime),
        ),
        ConsoleCard(
            "assignment",
            "Current Mission / Task",
            str(assignment.get("mission_id") or "Unassigned"),
            "active" if assignment else "idle",
            {
                "mission_id": assignment.get("mission_id"),
                "task": assignment.get("task") or assignment.get("task_id"),
                "source": assignment.get("source") or "existing_agent_task_lifecycle",
            },
        ),
    ]
    return ConsoleView("agent_detail", f"Agent Details — {agent.title}", cards)


def _capability_count(agents: Iterable[Any]) -> int:
    capabilities = {skill for agent in agents for skill in _skills(agent.lens)}
    return len(capabilities)


def _skills(lens: str) -> list[str]:
    return [item.strip() for item in str(lens or "").split(",") if item.strip()]


def _health_from_status(status: str) -> str:
    normalized = status.lower()
    if normalized in {"failed", "error", "offline", "blocked"}:
        return "degraded"
    if normalized in {"idle", "available", "ready", "active", "running"}:
        return "healthy"
    return "active"
