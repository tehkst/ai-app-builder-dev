from __future__ import annotations


RETRY = "retry"
ROLLBACK = "rollback"
ESCALATE = "escalate"
NO_ACTION = "no_action"


def recovery_plan(diagnosis: str) -> str:
    if diagnosis == "runtime_instability":
        return RETRY
    if diagnosis == "validation_failure":
        return ROLLBACK
    if diagnosis == "unknown_health_issue":
        return ESCALATE
    return NO_ACTION
