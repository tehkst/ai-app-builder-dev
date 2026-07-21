from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_reasoning_models import ExecutionPlan, PlanningAction


POLICY_ALLOW = "allow"
POLICY_MODIFY = "modify"
POLICY_REQUIRE_APPROVAL = "require_approval"
POLICY_DENY = "deny"


@dataclass(frozen=True)
class GovernedPrinciple:
    code: str
    title: str
    statement: str
    effect: str
    action_codes: Tuple[str, ...] = field(default_factory=tuple)
    priorities: Tuple[str, ...] = field(default_factory=tuple)
    requires_evidence: bool = False
    authoritative: bool = True

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "statement": self.statement,
            "effect": self.effect,
            "action_codes": list(self.action_codes),
            "priorities": list(self.priorities),
            "requires_evidence": self.requires_evidence,
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class PrincipleFinding:
    principle_code: str
    decision: str
    explanation: str
    action: PlanningAction | None = None
    related_entities: Tuple[CompanyBrainEntity, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "principle_code": self.principle_code,
            "decision": self.decision,
            "explanation": self.explanation,
            "action": self.action.as_dict() if self.action else None,
            "related_entities": [entity.as_dict() for entity in self.related_entities],
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class PolicyEvaluation:
    plan: ExecutionPlan
    decision: str
    findings: Tuple[PrincipleFinding, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    @property
    def executable(self) -> bool:
        return self.authoritative and self.decision in (POLICY_ALLOW, POLICY_MODIFY)

    @property
    def approval_required(self) -> bool:
        return self.decision == POLICY_REQUIRE_APPROVAL

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "plan": self.plan.as_dict(),
            "decision": self.decision,
            "findings": [finding.as_dict() for finding in self.findings],
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
            "executable": self.executable,
            "approval_required": self.approval_required,
        }
