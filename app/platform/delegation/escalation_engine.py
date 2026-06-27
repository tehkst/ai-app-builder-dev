from __future__ import annotations

from app.platform.delegation.manager_router import manager_for_capability


def requires_escalation(required_capability: str, candidate_count: int) -> bool:
    return candidate_count == 0


def escalation_target(required_capability: str, candidate_count: int) -> str:
    if not requires_escalation(required_capability, candidate_count):
        return ""
    return manager_for_capability(required_capability)
