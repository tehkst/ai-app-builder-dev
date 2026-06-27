from __future__ import annotations

from typing import List


def diagnose(anomalies: List[str]) -> str:
    if "validation_regression" in anomalies:
        return "validation_failure"
    if "repeated_job_failures" in anomalies:
        return "runtime_instability"
    if anomalies:
        return "unknown_health_issue"
    return "no_issue"
