from __future__ import annotations

from typing import Dict


def verify_outcome(supervision: Dict[str, object]) -> str:
    if supervision.get("status") == "scheduled":
        return "verification_pending"
    if supervision.get("status") == "skipped":
        return "verified_no_action"
    return "verification_failed"
