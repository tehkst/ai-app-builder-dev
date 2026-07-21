from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainRelationship,
)


@dataclass(frozen=True)
class ReasoningEvidence:
    entity: CompanyBrainEntity
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "entity": self.entity.as_dict(),
            "supporting_event_ids": list(self.supporting_event_ids),
        }


@dataclass(frozen=True)
class ReasoningFinding:
    code: str
    title: str
    description: str
    severity: str = "info"
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    related_entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "supporting_event_ids": list(self.supporting_event_ids),
            "related_entities": [entity.as_dict() for entity in self.related_entities],
        }


@dataclass(frozen=True)
class ExecutionSummary:
    mission: CompanyBrainEntity
    entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    relationships: Tuple[CompanyBrainRelationship, ...] = field(default_factory=tuple)
    evidence: Tuple[ReasoningEvidence, ...] = field(default_factory=tuple)
    findings: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "mission": self.mission.as_dict(),
            "entities": [entity.as_dict() for entity in self.entities],
            "relationships": [relationship.as_dict() for relationship in self.relationships],
            "evidence": [item.as_dict() for item in self.evidence],
            "findings": [finding.as_dict() for finding in self.findings],
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class ImpactSummary:
    subject: CompanyBrainEntity
    upstream: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    downstream: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    affected: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    risk_score: int = 0
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "subject": self.subject.as_dict(),
            "upstream": [entity.as_dict() for entity in self.upstream],
            "downstream": [entity.as_dict() for entity in self.downstream],
            "affected": [entity.as_dict() for entity in self.affected],
            "risk_score": self.risk_score,
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class RootCauseSummary:
    failure: CompanyBrainEntity
    contributing_factors: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    evidence: Tuple[ReasoningEvidence, ...] = field(default_factory=tuple)
    likely_cause: str = ""
    confidence: float = 0.0
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "failure": self.failure.as_dict(),
            "contributing_factors": [finding.as_dict() for finding in self.contributing_factors],
            "evidence": [item.as_dict() for item in self.evidence],
            "likely_cause": self.likely_cause,
            "confidence": self.confidence,
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class DecisionExplanation:
    decision: CompanyBrainEntity
    reason: str = ""
    evidence: Tuple[ReasoningEvidence, ...] = field(default_factory=tuple)
    dependencies: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    affected_systems: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "decision": self.decision.as_dict(),
            "reason": self.reason,
            "evidence": [item.as_dict() for item in self.evidence],
            "dependencies": [entity.as_dict() for entity in self.dependencies],
            "affected_systems": [entity.as_dict() for entity in self.affected_systems],
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class PlanningAction:
    sequence: int
    code: str
    title: str
    description: str
    priority: str = "normal"
    target_entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "sequence": self.sequence,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "target_entities": [entity.as_dict() for entity in self.target_entities],
            "supporting_event_ids": list(self.supporting_event_ids),
        }


@dataclass(frozen=True)
class ExecutionPlan:
    mission: CompanyBrainEntity
    actions: Tuple[PlanningAction, ...] = field(default_factory=tuple)
    blockers: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "mission": self.mission.as_dict(),
            "actions": [action.as_dict() for action in self.actions],
            "blockers": [blocker.as_dict() for blocker in self.blockers],
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class ActionExecution:
    sequence: int
    action_code: str
    status: str
    message: str = ""
    target_entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "sequence": self.sequence,
            "action_code": self.action_code,
            "status": self.status,
            "message": self.message,
            "target_entities": [entity.as_dict() for entity in self.target_entities],
            "supporting_event_ids": list(self.supporting_event_ids),
        }


@dataclass(frozen=True)
class ExecutionRun:
    mission: CompanyBrainEntity
    plan: ExecutionPlan
    action_executions: Tuple[ActionExecution, ...] = field(default_factory=tuple)
    status: str = "pending"
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "mission": self.mission.as_dict(),
            "plan": self.plan.as_dict(),
            "action_executions": [item.as_dict() for item in self.action_executions],
            "status": self.status,
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }
