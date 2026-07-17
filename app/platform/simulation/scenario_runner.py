from __future__ import annotations

from typing import Any

from app.platform.simulation.simulation_session import SimulationSession


class ScenarioRunner:
    def run(self, session: SimulationSession, twin_snapshot: dict[str, Any]) -> dict[str, Any]:
        session.status = "completed"
        return {
            "session_id": session.session_id, "scenario": session.scenario.name,
            "status": "placeholder", "production_mutated": False,
            "input_revision": twin_snapshot.get("last_event_id"),
        }
