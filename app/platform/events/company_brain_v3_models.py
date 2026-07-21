from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from app.platform.events.company_brain_evolution_models import EvolutionCycle
from app.platform.events.company_brain_mission_reasoning_models import MissionReasoningAssessment
from app.platform.events.company_brain_principle_models import PolicyEvaluation
from app.platform.events.company_brain_reasoning_models import ExecutionPlan, ExecutionRun
from app.platform.events.company_brain_twin_models import DigitalTwinSnapshot


MISSION_READY = "ready"
MISSION_BLOCKED = "blocked"
MISSION_APPROVAL_REQUIRED = "approval_required"
MISSION_COMPLETED = "completed"
MISSION_PENDING = "pending"
MISSION_FAILED = "failed"


@dataclass(frozen=True)
class CompanyBrainV3Result:
    """Immutable aggregate of existing governed subsystem outputs."""

    mission_id: str
    reasoning: MissionReasoningAssessment
    plan: ExecutionPlan
    policy: PolicyEvaluation
    twin: DigitalTwinSnapshot
    execution: Optional[ExecutionRun] = None
    evolution: Optional[EvolutionCycle] = None
    status: str = MISSION_READY
    next_action: str = ""
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    supporting_event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    @property
    def terminal(self) -> bool:
        return self.status in {MISSION_BLOCKED, MISSION_COMPLETED, MISSION_FAILED}

    @property
    def approval_required(self) -> bool:
        return self.status == MISSION_APPROVAL_REQUIRED

    @property
    def executable(self) -> bool:
        return self.policy.executable

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "mission_id": self.mission_id,
            "reasoning": self.reasoning.as_dict(),
            "plan": self.plan.as_dict(),
            "policy": self.policy.as_dict(),
            "twin": self.twin.as_dict(),
            "execution": self.execution.as_dict() if self.execution else None,
            "evolution": self.evolution.as_dict() if self.evolution else None,
            "status": self.status,
            "next_action": self.next_action,
            "warnings": list(self.warnings),
            "supporting_event_ids": list(self.supporting_event_ids),
            "authoritative": self.authoritative,
            "terminal": self.terminal,
            "approval_required": self.approval_required,
            "executable": self.executable,
        }
