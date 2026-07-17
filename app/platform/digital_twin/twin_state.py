from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TwinState:
    missions: dict[str, dict[str, Any]] = field(default_factory=dict)
    workflows: dict[str, dict[str, Any]] = field(default_factory=dict)
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    board_room_decisions: list[dict[str, Any]] = field(default_factory=list)
    last_event_id: str = ""

    def snapshot(self) -> dict[str, Any]:
        return {
            "missions": dict(self.missions), "workflows": dict(self.workflows),
            "agents": dict(self.agents), "tasks": dict(self.tasks),
            "board_room_decisions": list(self.board_room_decisions),
            "last_event_id": self.last_event_id,
        }
