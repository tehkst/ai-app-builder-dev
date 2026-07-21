from __future__ import annotations

from app.platform.events.company_brain_learning_engine import CompanyBrainLearningEngine
from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_reasoning_models import (
    ActionExecution,
    ExecutionPlan,
    ExecutionRun,
    PlanningAction,
)


def _plan() -> ExecutionPlan:
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


def _completed_run() -> ExecutionRun:
    plan = _plan()
    return ExecutionRun(
        mission=plan.mission,
        plan=plan,
        action_executions=(
            ActionExecution(
                sequence=1,
                action_code="EXECUTE_DEPENDENCY_SEQUENCE",
                status="completed",
                message="Dependencies completed.",
                target_entities=plan.actions[0].target_entities,
                supporting_event_ids=("event-1",),
            ),
            ActionExecution(
                sequence=2,
                action_code="VERIFY_MISSION_OUTCOME",
                status="completed",
                message="Mission outcome verified.",
                target_entities=plan.actions[1].target_entities,
                supporting_event_ids=("event-2",),
            ),
        ),
        status="completed",
        supporting_event_ids=("event-1", "event-2"),
        authoritative=True,
    )


def _failed_run() -> ExecutionRun:
    plan = _plan()
    return ExecutionRun(
        mission=plan.mission,
        plan=plan,
        action_executions=(
            ActionExecution(
                sequence=1,
                action_code="EXECUTE_DEPENDENCY_SEQUENCE",
                status="failed",
                message="RuntimeError: dependency failed",
                target_entities=plan.actions[0].target_entities,
                supporting_event_ids=("event-1",),
            ),
            ActionExecution(
                sequence=2,
                action_code="VERIFY_MISSION_OUTCOME",
                status="skipped",
                message="Skipped because a prior action failed.",
                target_entities=plan.actions[1].target_entities,
                supporting_event_ids=("event-2",),
            ),
        ),
        status="failed",
        supporting_event_ids=("event-1", "event-2"),
        authoritative=False,
    )


def _check_authoritative_learning() -> None:
    summary = CompanyBrainLearningEngine().learn_from_execution(_completed_run())

    assert summary.authoritative is True
    assert len(summary.candidates) == 2
    assert len(summary.lessons) == 2
    assert summary.patterns == ()
    assert all(candidate.authoritative for candidate in summary.candidates)
    assert all(lesson.authoritative for lesson in summary.lessons)
    assert all(lesson.confidence == 1.0 for lesson in summary.lessons)
    assert summary.supporting_event_ids == ("event-1", "event-2")
    serialized = summary.as_dict()
    assert serialized["mission"]["entity_id"] == "mission-1"
    assert serialized["lessons"][0]["outcome"] == "completed"


def _check_non_authoritative_failure_learning() -> None:
    summary = CompanyBrainLearningEngine().learn_from_execution(_failed_run())

    assert summary.authoritative is False
    assert len(summary.candidates) == 2
    assert summary.lessons == ()
    assert summary.candidates[0].outcome == "failed"
    assert summary.candidates[0].confidence == 0.6
    assert summary.candidates[0].authoritative is False
    assert "One or more execution runs are non-authoritative." in summary.warnings
    assert "No candidate qualified as governed authoritative learning." in summary.warnings


def _check_repeated_pattern_detection() -> None:
    run = _completed_run()
    summary = CompanyBrainLearningEngine().learn_from_executions((run, run))

    assert len(summary.patterns) == 2
    assert tuple(pattern.action_code for pattern in summary.patterns) == (
        "EXECUTE_DEPENDENCY_SEQUENCE",
        "VERIFY_MISSION_OUTCOME",
    )
    assert all(pattern.occurrences == 2 for pattern in summary.patterns)
    assert all(pattern.authoritative for pattern in summary.patterns)
    assert all(pattern.confidence == 1.0 for pattern in summary.patterns)


def _check_missing_evidence_is_not_governed() -> None:
    plan = _plan()
    run = ExecutionRun(
        mission=plan.mission,
        plan=plan,
        action_executions=(
            ActionExecution(
                sequence=1,
                action_code="VERIFY_MISSION_OUTCOME",
                status="completed",
                message="Verified without evidence.",
            ),
        ),
        status="completed",
        authoritative=True,
    )
    summary = CompanyBrainLearningEngine().learn_from_execution(run)

    assert summary.authoritative is False
    assert summary.lessons == ()
    assert summary.candidates[0].confidence == 0.0
    assert "One or more learning candidates have no supporting event evidence." in summary.warnings


def _check_validation() -> None:
    engine = CompanyBrainLearningEngine()
    try:
        engine.learn_from_executions(())
    except ValueError as error:
        assert str(error) == "at least one execution run is required"
    else:
        raise AssertionError("empty execution history must fail")

    try:
        engine.learn_from_executions((_completed_run(), None))  # type: ignore[arg-type]
    except TypeError as error:
        assert str(error) == "runs must contain only ExecutionRun values"
    else:
        raise AssertionError("invalid execution history must fail")

    other = _completed_run()
    other_mission = CompanyBrainEntity("PlatformMission", "mission-2")
    mismatched = ExecutionRun(
        mission=other_mission,
        plan=other.plan,
        action_executions=other.action_executions,
        status=other.status,
        supporting_event_ids=other.supporting_event_ids,
        authoritative=other.authoritative,
    )
    try:
        engine.learn_from_executions((other, mismatched))
    except ValueError as error:
        assert str(error) == "all execution runs must belong to the same mission"
    else:
        raise AssertionError("mixed missions must fail")


def main() -> None:
    _check_authoritative_learning()
    _check_non_authoritative_failure_learning()
    _check_repeated_pattern_detection()
    _check_missing_evidence_is_not_governed()
    _check_validation()
    print("company brain learning engine: PASS")


if __name__ == "__main__":
    main()
