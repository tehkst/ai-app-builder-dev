from __future__ import annotations

from app.platform.constitution.policy_engine import blocking_rules_for_target


def approval_required(target: str) -> bool:
    return bool(blocking_rules_for_target(target))


def approval_status(target: str, approved: bool = False) -> str:
    if not approval_required(target):
        return "not_required"
    return "approved" if approved else "required"
