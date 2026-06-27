from __future__ import annotations

from typing import Dict, List

from app.platform.learning.experience_store import ExperienceRecord


def success_rate(records: List[ExperienceRecord], task_type: str) -> float:
    scoped = [record for record in records if record.task_type == task_type]
    if not scoped:
        return 0.0
    successes = [record for record in scoped if record.outcome == "success"]
    return len(successes) / len(scoped)


def agent_success_rates(records: List[ExperienceRecord]) -> Dict[str, float]:
    agents = sorted({record.agent_id for record in records})
    rates: Dict[str, float] = {}
    for agent_id in agents:
        scoped = [record for record in records if record.agent_id == agent_id]
        successes = [record for record in scoped if record.outcome == "success"]
        rates[agent_id] = len(successes) / len(scoped) if scoped else 0.0
    return rates
