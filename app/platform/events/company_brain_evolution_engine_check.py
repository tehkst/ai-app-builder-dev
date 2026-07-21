from __future__ import annotations

from app.platform.events.company_brain_evolution_engine import CompanyBrainEvolutionEngine
from app.platform.events.company_brain_evolution_models import (
    EVOLUTION_COMPLETE,
    EVOLUTION_REPLAN,
    EVOLUTION_REQUIRE_APPROVAL,
    EVOLUTION_STOP,
)
from app.platform.events.company_brain_mission_reasoning_models import MissionReasoningAssessment
from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_principle_models import (
    POLICY_ALLOW,
    POLICY_DENY,
    POLICY_REQUIRE_APPROVAL,
    PolicyEvaluation,
)
from app.platform.events.company_brain_reasoning_models import (
    ActionExecution,
    ExecutionPlan,
    ExecutionRun,
    ExecutionSummary,
    PlanningAction,
)


MISSION = CompanyBrainEntity("PlatformMission", "mission-1")
EVENTS = ("event-1",)


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        mission=MISSION,
        actions=(
            PlanningAction(
                sequence=1,
                code="IMPLEMENT_CHANGE",
                title="Implement change",
                description="Implement the governed change.",
                target_entities=(MISSION,),
                supporting_event_ids=EVENTS,
            ),
        ),
        supporting_event_ids=EVENTS,
        authoritative=True,
    )


class _ReasoningEngine:
    def assess_mission(self, mission_id: str) -> MissionReasoningAssessment:
        assert mission_id == "mission-1"
        return MissionReasoningAssessment(
            summary=ExecutionSummary(
                mission=MISSION,
                entities=(MISSION,),
                supporting_event_ids=EVENTS,
                authoritative=True,
            ),
            recommended_strategy="PROCEED_TO_GOVERNED_PLANNING",
            next_best_action="Generate a revised governed plan.",
            confidence=1.0,
            supporting_event_ids=EVENTS,
            authoritative=True,
        )


class _PlanningEngine:
    def generate_execution_plan(self, mission_id: str) -> ExecutionPlan:
        assert mission_id == "mission-1"
        return _plan()


class _PrincipleEngine:
    def __init__(self, decision: str = POLICY_ALLOW) -> None:
        self._decision = decision

    def evaluate_plan(self, plan: ExecutionPlan) -> PolicyEvaluation:
        return PolicyEvaluation(
            plan=plan,
            decision=self._decision,
            supporting_event_ids=EVENTS,
            authoritative=True,
        )


def _engine(decision: str = POLICY_ALLOW) -> CompanyBrainEvolutionEngine:
    return CompanyBrainEvolutionEngine(
        mission_reasoning_engine=_ReasoningEngine(),
        planning_engine=_PlanningEngine(),
        principle_engine=_PrincipleEngine(decision),
    )


def _run(status: str, action_status: str, action_code: str = "IMPLEMENT_CHANGE") -> ExecutionRun:
    return ExecutionRun(
        mission=MISSION,
        plan=_plan(),
        action_executions=(
            ActionExecution(
                sequence=1,
                action_code=action_code,
                status=action_status,
                message="recorded outcome",
                target_entities=(MISSION,),
                supporting_event_ids=EVENTS,
            ),
        ),
        status=status,
        supporting_event_ids=EVENTS,
        authoritative=True,
    )


def _check_complete() -> None:
    cycle = _engine().evolve(_run("completed", "completed"))
    assert cycle.disposition == EVOLUTION_COMPLETE
    assert cycle.terminal is True
    assert cycle.should_continue is False
    assert cycle.observation.completed_actions == ("IMPLEMENT_CHANGE",)
    assert cycle.learning.authoritative is True
    assert cycle.authoritative is True
    assert cycle.as_dict()["disposition"] == EVOLUTION_COMPLETE


def _check_replan() -> None:
    cycle = _engine().evolve(_run("failed", "failed"))
    assert cycle.disposition == EVOLUTION_REPLAN
    assert cycle.should_continue is True
    assert cycle.observation.failed_actions == ("IMPLEMENT_CHANGE",)
    assert any(
        finding.code == "EXECUTION_DIVERGED_FROM_EXPECTATION"
        for finding in cycle.observation.findings
    )


def _check_approval() -> None:
    cycle = _engine(POLICY_REQUIRE_APPROVAL).evolve(
        _run("completed", "completed")
    )
    assert cycle.disposition == EVOLUTION_REQUIRE_APPROVAL
    assert cycle.approval_required is True


def _check_policy_stop() -> None:
    cycle = _engine(POLICY_DENY).evolve(_run("completed", "completed"))
    assert cycle.disposition == EVOLUTION_STOP
    assert cycle.terminal is True


def _check_unexpected_action() -> None:
    cycle = _engine().evolve(_run("completed", "completed", "UNPLANNED_CHANGE"))
    assert cycle.disposition == EVOLUTION_STOP
    assert cycle.observation.unexpected_actions == ("UNPLANNED_CHANGE",)
    assert cycle.observation.authoritative is False


def _check_validation() -> None:
    try:
        _engine().evolve(object())
    except TypeError as exc:
        assert str(exc) == "run must be an ExecutionRun"
    else:
        raise AssertionError("invalid evolution input was accepted")


def main() -> None:
    _check_complete()
    _check_replan()
    _check_approval()
    _check_policy_stop()
    _check_unexpected_action()
    _check_validation()
    print("company brain evolution engine: PASS")


if __name__ == "__main__":
    main()
