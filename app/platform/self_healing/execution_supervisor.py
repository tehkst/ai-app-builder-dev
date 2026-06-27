from __future__ import annotations

from typing import Dict


def supervise_action(plan: str) -> Dict[str, object]:
    return {
        "plan": plan,
        "accepted": plan != "no_action",
        "status": "scheduled" if plan != "no_action" else "skipped",
    }
