from __future__ import annotations

from typing import List

from app.platform.learning.experience_store import ExperienceRecord
from app.platform.learning.pattern_detector import success_rate


def confidence_score(records: List[ExperienceRecord], task_type: str) -> int:
    rate = success_rate(records, task_type)
    sample_size = len([record for record in records if record.task_type == task_type])
    sample_factor = min(sample_size, 100) / 100
    return int(rate * sample_factor * 100)


def confidence_label(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"
