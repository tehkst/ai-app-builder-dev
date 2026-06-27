from __future__ import annotations

from typing import Dict


def audit_transition(job_id: str, previous_state: str, next_state: str) -> Dict[str, str]:
    return {
        "job_id": job_id,
        "previous_state": previous_state,
        "next_state": next_state,
    }
