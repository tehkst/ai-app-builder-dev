from __future__ import annotations

from typing import Dict, List

from app.platform.learning.experience_store import ExperienceRecord
from app.platform.learning.optimization_engine import optimization_hint
from app.platform.learning.recommendation_engine import recommend_agent


def decision_intelligence(records: List[ExperienceRecord], task_type: str) -> Dict[str, object]:
    recommendation = recommend_agent(records, task_type)
    return {
        "task_type": task_type,
        "recommendation": recommendation,
        "optimization_hint": optimization_hint(recommendation),
    }
