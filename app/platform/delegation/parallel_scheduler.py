from __future__ import annotations

from typing import Dict, List

from app.platform.delegation.availability import available_agents
from app.platform.delegation.capability_index import agents_for_capability
from app.platform.delegation.load_tracker import load_for_agent
from app.platform.delegation.request_model import DelegationRequest


def best_agent_for_request(request: DelegationRequest) -> str:
    capable = agents_for_capability(request.required_capability)
    available = available_agents(capable)
    if not available:
        return ""
    return sorted(available, key=lambda agent_id: (load_for_agent(agent_id), agent_id))[0]


def schedule_requests(requests: List[DelegationRequest]) -> Dict[str, str]:
    assignments: Dict[str, str] = {}
    for request in sorted(requests, key=lambda item: (item.priority, item.request_id)):
        agent_id = best_agent_for_request(request)
        if agent_id:
            assignments[request.request_id] = agent_id
    return assignments
