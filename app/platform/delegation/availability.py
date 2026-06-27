from __future__ import annotations

from typing import List

from app.platform.delegation.load_tracker import runtime_profiles


def available_agents(agent_ids: List[str]) -> List[str]:
    profiles = runtime_profiles()
    return [
        agent_id
        for agent_id in agent_ids
        if profiles.get(agent_id) is not None
        and profiles[agent_id].status == "available"
        and profiles[agent_id].health_score >= 80
    ]
