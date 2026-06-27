from __future__ import annotations

from typing import Dict

from app.platform.delegation.capability_index import capability_map
from app.platform.delegation.runtime_profile import RuntimeProfile


def runtime_profiles() -> Dict[str, RuntimeProfile]:
    agent_ids = sorted({agent for agents in capability_map().values() for agent in agents})
    return {
        agent_id: RuntimeProfile(
            agent_id=agent_id,
            status="available",
            current_load=0,
            queue_depth=0,
            health_score=100,
        )
        for agent_id in agent_ids
    }


def load_for_agent(agent_id: str) -> int:
    profile = runtime_profiles().get(agent_id)
    return profile.current_load if profile else 999
