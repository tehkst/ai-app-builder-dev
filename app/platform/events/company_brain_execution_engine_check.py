from __future__ import annotations

from app.platform.events.company_brain_execution_engine import CompanyBrainExecutionEngine
from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_reasoning_models import (
    ExecutionPlan,
    PlanningAction,
    ReasoningFinding,
)


class _FakePlanningEngine:
    def __init__(self, plan: ExecutionPlan) -> None:
        self._plan = plan
        self.calls = []

    def generate_execution_plan(self, mission_id: str) -> ExecutionPlan:
        self.calls.append(mission_id)
        return self._plan


def _authoritative_plan() -> ExecutionPlan:
    mission = CompanyBrainEntity("PlatformMission", "mission-1")
    workflow = CompanyBrainEntity("PlatformWorkflowRun", "workflow-1")
    return ExecutionPlan(
        mission=mission,
        actions=(
            PlanningAction(
                sequence=1,
                code="EXECUTE_DEPENDENCY_SEQUENCE",
                title="Execute dependencies",
                description="Execute dependencies deterministically.",
                target_entities=(workflow,),
                supporting_event_ids=("event-1",),
            ),
            PlanningAction(
                sequence=2,
                code="VERIFY_MISSION_OUTCOME",
                title="Verify outcome",
                description="Verify the mission outcome.",
                target_entities=(mission,),
                supporting_event_ids=("event-2",),
            ),
        ),
        supporting_event_ids=("event-1", "event-2"),
        authoritative=True,
    )


def _check_completed_execution() -> None:
    planning = _FakePlanningEngine(_authoritative_plan())
    calls = []

    def handler(action: PlanningAction) -> str:
        calls.append(action.code)
        return "completed %s" % action.code

    run = CompanyBrainExecutionEngine(
        planning,
        handlers={"*": handler},
    ).execute_mission("mission-1")

    assert planning.calls == ["mission-1"]
    assert calls == ["EXECUTE_DEPENDENCY_SEQUENCE", "VERIFY_MISSION_OUTCOME"]
    assert run.status == "completed"
    assert run.authoritative is True
    assert tuple(item.status for item in run.action_executions) == (
        "completed",
        "completed",
    )
    assert run.supporting_event_ids == ("event-1", "event-2")
    serialized = run.as_dict()
    assert serialized["mission"]["entity_id"] == "mission-1"
    assert serialized["action_executions"][0]["sequence"] == 1


def _check_pending_execution() -> None:
    run = CompanyBrainExecutionEngine(
        _FakePlanningEngine(_authoritative_plan())
    ).execute_mission("mission-1")

    assert run.status == "pending"
    assert run.authoritative is False
    assert tuple(item.status for item in run.action_executions) == (
        "pending",
        "pending",
    )


def _check_failed_execution() -> None:
    def fail(_: PlanningAction) -> str:
        raise RuntimeError("dependency execution failed")

    called = []

    def verify(action: PlanningAction) -> str:
        called.append(action.code)
        return "verified"

    run = CompanyBrainExecutionEngine(
        _FakePlanningEngine(_authoritative_plan()),
        handlers={
            "EXECUTE_DEPENDENCY_SEQUENCE": fail,
            "VERIFY_MISSION_OUTCOME": verify,
        },
    ).execute_mission("mission-1")

    assert run.status == "failed"
    assert run.authoritative is False
    assert tuple(item.status for item in run.action_executions) == (
        "failed",
        "skipped",
    )
    assert "RuntimeError" in run.action_executions[0].message
    assert called == []


def _check_blocked_execution() -> None:
    mission = CompanyBrainEntity("PlatformMission", "mission-2")
    blocker = ReasoningFinding(
        code="MISSION_NOT_GOVERNED",
        title="Mission is not governed",
        description="Project the mission first.",
        severity="error",
        related_entities=(mission,),
    )
    plan = ExecutionPlan(
        mission=mission,
        actions=(
            PlanningAction(
                sequence=1,
                code="RESOLVE_MISSION_NOT_GOVERNED",
                title="Resolve mission governance",
                description="Project the mission.",
                target_entities=(mission,),
            ),
        ),
        blockers=(blocker,),
        authoritative=False,
    )
    called = []

    def handler(action: PlanningAction) -> str:
        called.append(action.code)
        return "unexpected"

    run = CompanyBrainExecutionEngine(
        _FakePlanningEngine(plan),
        handlers={"*": handler},
    ).execute_mission("mission-2")

    assert run.status == "blocked"
    assert run.action_executions[0].status == "blocked"
    assert run.authoritative is False
    assert called == []


def _check_validation() -> None:
    engine = CompanyBrainExecutionEngine(_FakePlanningEngine(_authoritative_plan()))
    try:
        engine.execute_mission(" ")
    except ValueError as error:
        assert str(error) == "mission_id is required"
    else:
        raise AssertionError("blank mission_id must fail")

    try:
        engine.execute_plan(None)  # type: ignore[arg-type]
    except TypeError as error:
        assert str(error) == "plan must be an ExecutionPlan"
    else:
        raise AssertionError("invalid plan must fail")


def main() -> None:
    _check_completed_execution()
    _check_pending_execution()
    _check_failed_execution()
    _check_blocked_execution()
    _check_validation()
    print("company brain execution engine: PASS")


if __name__ == "__main__":
    main()
