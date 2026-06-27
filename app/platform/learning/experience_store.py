from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ExperienceRecord:
    experience_id: str
    task_type: str
    agent_id: str
    outcome: str
    duration_seconds: int
    retry_count: int
    recovery_action: Optional[str]
    quality_score: int


def add_experience(records: List[ExperienceRecord], record: ExperienceRecord) -> List[ExperienceRecord]:
    return records + [record]


def successful_experiences(records: List[ExperienceRecord]) -> List[ExperienceRecord]:
    return [record for record in records if record.outcome == "success"]
