from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from app.platform.events.company_brain_models import CompanyBrainEntity


@dataclass(frozen=True)
class LearningCandidate:
    code: str
    title: str
    description: str
    outcome: str
    confidence: float
    target_entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "target_entities": [entity.as_dict() for entity in self.target_entities],
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class LearnedLesson:
    code: str
    statement: str
    outcome: str
    confidence: float
    target_entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "code": self.code,
            "statement": self.statement,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "target_entities": [entity.as_dict() for entity in self.target_entities],
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class LearningPattern:
    code: str
    action_code: str
    outcome: str
    occurrences: int
    confidence: float
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "code": self.code,
            "action_code": self.action_code,
            "outcome": self.outcome,
            "occurrences": self.occurrences,
            "confidence": self.confidence,
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class LearningSummary:
    mission: CompanyBrainEntity
    candidates: Tuple[LearningCandidate, ...] = field(default_factory=tuple)
    lessons: Tuple[LearnedLesson, ...] = field(default_factory=tuple)
    patterns: Tuple[LearningPattern, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "mission": self.mission.as_dict(),
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "lessons": [lesson.as_dict() for lesson in self.lessons],
            "patterns": [pattern.as_dict() for pattern in self.patterns],
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }
