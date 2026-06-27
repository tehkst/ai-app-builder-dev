from __future__ import annotations

from typing import Dict


def optimization_hint(recommendation: Dict[str, object]) -> str:
    confidence = int(recommendation.get("confidence", 0))
    if confidence >= 80:
        return "auto_apply"
    if confidence >= 50:
        return "manager_review"
    return "collect_more_data"
