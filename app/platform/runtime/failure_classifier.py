from __future__ import annotations

TRANSIENT = "transient"
PERMANENT = "permanent"
DEPENDENCY = "dependency"
INFRASTRUCTURE = "infrastructure"
POLICY = "policy"
AGENT = "agent"
UNKNOWN = "unknown"

RETRYABLE_FAILURES = {TRANSIENT, DEPENDENCY, INFRASTRUCTURE}
ESCALATION_FAILURES = {PERMANENT, POLICY, AGENT, UNKNOWN}


def classify_failure(error: str) -> str:
    value = error.lower()
    if "timeout" in value or "temporary" in value:
        return TRANSIENT
    if "dependency" in value or "import" in value:
        return DEPENDENCY
    if "policy" in value or "constitution" in value:
        return POLICY
    if "agent" in value:
        return AGENT
    if "permanent" in value or "invalid" in value:
        return PERMANENT
    return UNKNOWN


def is_retryable(failure_type: str) -> bool:
    return failure_type in RETRYABLE_FAILURES
