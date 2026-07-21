from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from app.platform.events.company_brain_learning_models import LearningSummary
from app.platform.events.company_brain_mission_reasoning_models import MissionReasoningAssessment
from app.platform.events.company_brain_principle_models import PolicyEvaluation
from app.platform.events.company_brain_reasoning_models import ExecutionPlan, ExecutionRun, ReasoningFinding


EVOLUTION_COMPLETE = "complete"
EVOLUTION_CONTINUE = "continue"
EVOLUTION_REPLAN = "replan"
EVOLUTION_REQUIRE_APPROVAL = "require_approval"
EVOLUTION_STOP = "stop"


@dataclass(frozen=True)
class ExecutionObservation:
    expected_actions: Tuple[str, ...] = field(default_factory=tuple)
    completed_actions: Tuple[str, ...] = field(default_factory=tuple)
    failed_actions: Tuple[str, ...] = field(default_factory=tuple)
    blocked_actions: Tuple[str, ...] = field(default_factory=tuple)
    pending_actions: Tuple[str, ...] = field(default_factory=tuple)
    skipped_actions: Tuple[str, ...] = field(default_factory=tuple)
    unexpected_actions: Tuple[str, ...] = field(default_factory=tuple)
    findings: Tuple[ReasoningFinding, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "expected_actions": list(self.expected_actions),
            "completed_actions": list(self.completed_actions),
            "failed_actions": list(self.failed_actions),
            "blocked_actions": list(self.blocked_actions),
            "pending_actions": list(self.pending_actions),
            "skipped_actions": list(self.skipped_actions),
            "unexpected_actions": list(self.unexpected_actions),
            "findings": [finding.as_dict() for finding in self.findings],
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class EvolutionCycle:
    run: ExecutionRun
    observation: ExecutionObservation
    learning: LearningSummary
    reasoning: MissionReasoningAssessment
    revised_plan: ExecutionPlan
    policy: PolicyEvaluation
    disposition: str
    next_action: str = ""
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    @property
    def should_continue(self) -> bool:
        return self.disposition in {EVOLUTION_CONTINUE, EVOLUTION_REPLAN}

    @property
    def approval_required(self) -> bool:
        return self.disposition == EVOLUTION_REQUIRE_APPROVAL

    @property
    def terminal(self) -> bool:
        return self.disposition in {EVOLUTION_COMPLETE, EVOLUTION_STOP}

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "run": self.run.as_dict(),
            "observation": self.observation.as_dict(),
            "learning": self.learning.as_dict(),
            "reasoning": self.reasoning.as_dict(),
            "revised_plan": self.revised_plan.as_dict(),
            "policy": self.policy.as_dict(),
            "disposition": self.disposition,
            "next_action": self.next_action,
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
            "should_continue": self.should_continue,
            "approval_required": self.approval_required,
            "terminal": self.terminal,
        }
