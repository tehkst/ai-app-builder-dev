from __future__ import annotations

from dataclasses import replace

from app.platform.learning.experience_store import ExperienceRecord


def apply_quality_feedback(record: ExperienceRecord, quality_score: int) -> ExperienceRecord:
    return replace(record, quality_score=quality_score)


def outcome_from_feedback(quality_score: int) -> str:
    return "success" if quality_score >= 70 else "failed"
