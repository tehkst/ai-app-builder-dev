from __future__ import annotations

from app.platform.delegation.capability_index import agents_for_capability
from app.platform.delegation.decision_model import DelegationDecision
from app.platform.delegation.request_model import DelegationRequest


def choose_agent(required_capability: str) -> str | None:
    candidates = agents_for_capability(required_capability)
    if not candidates:
        return None
    return sorted(candidates)[0]


def delegate(request: DelegationRequest) -> DelegationDecision:
    candidates = agents_for_capability(request.required_capability)
    selected = choose_agent(request.required_capability)
    return DelegationDecision(
        request_id=request.request_id,
        selected_agent_id=selected,
        candidate_agent_ids=candidates,
        reason="selected first active capability match" if selected else "no matching capability",
        allowed=selected is not None,
    )
