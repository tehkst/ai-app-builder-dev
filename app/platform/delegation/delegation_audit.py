from __future__ import annotations

from typing import Dict

from app.platform.delegation.decision_model import DelegationDecision


def audit_decision(decision: DelegationDecision, manager_id: str) -> Dict[str, object]:
    return {
        "request_id": decision.request_id,
        "manager_id": manager_id,
        "selected_agent_id": decision.selected_agent_id,
        "candidate_agent_ids": list(decision.candidate_agent_ids),
        "allowed": decision.allowed,
        "reason": decision.reason,
    }
