from __future__ import annotations

from typing import Dict, List

from app.platform.learning.confidence_engine import confidence_score
from app.platform.learning.experience_store import ExperienceRecord
from app.platform.learning.pattern_detector import agent_success_rates


def recommend_agent(records: List[ExperienceRecord], task_type: str) -> Dict[str, object]:
    scoped = [record for record in records if record.task_type == task_type]
    rates = agent_success_rates(scoped)
    if not rates:
        return {"agent_id": "", "confidence": 0, "reason": "no experience"}
    agent_id = sorted(rates, key=lambda item: (-rates[item], item))[0]
    return {
        "agent_id": agent_id,
        "confidence": confidence_score(scoped, task_type),
        "reason": "highest historical success rate",
    }
