from __future__ import annotations

from typing import List

from app.platform.delegation.load_tracker import load_for_agent


def least_loaded(agent_ids: List[str]) -> str:
    if not agent_ids:
        return ""
    return sorted(agent_ids, key=lambda agent_id: (load_for_agent(agent_id), agent_id))[0]


def first_available(agent_ids: List[str]) -> str:
    if not agent_ids:
        return ""
    return sorted(agent_ids)[0]
