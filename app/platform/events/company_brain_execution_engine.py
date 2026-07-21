from __future__ import annotations

from typing import Callable, Iterable, Mapping, Optional, Tuple

from app.platform.events.company_brain_planning_engine import CompanyBrainPlanningEngine
from app.platform.events.company_brain_reasoning_models import (
    ActionExecution,
    ExecutionPlan,
    ExecutionRun,
    PlanningAction,
)

ActionHandler = Callable[[PlanningAction], Optional[str]]


class CompanyBrainExecutionEngine:
    """Execute governed plans through explicitly registered deterministic handlers."""

    def __init__(
        self,
        planning_engine: Optional[CompanyBrainPlanningEngine] = None,
        handlers: Optional[Mapping[str, ActionHandler]] = None,
    ) -> None:
        self._planning_engine = planning_engine or CompanyBrainPlanningEngine()
        self._handlers = dict(handlers or {})

    def execute_mission(self, mission_id: str) -> ExecutionRun:
        normalized_id = _required(mission_id, "mission_id")
        plan = self._planning_engine.generate_execution_plan(normalized_id)
        return self.execute_plan(plan)

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionRun:
        if not isinstance(plan, ExecutionPlan):
            raise TypeError("plan must be an ExecutionPlan")

        if plan.blockers or not plan.authoritative:
            executions = tuple(
                _execution(
                    action,
                    status="blocked",
                    message="Execution is blocked until the governed plan is authoritative.",
                )
                for action in plan.actions
            )
            return _run(plan, executions, "blocked", authoritative=False)

        executions = []
        failed = False
        pending = False

        for action in sorted(plan.actions, key=lambda item: item.sequence):
            if failed:
                executions.append(
                    _execution(
                        action,
                        status="skipped",
                        message="Skipped because a prior action failed.",
                    )
                )
                continue

            handler = self._handlers.get(action.code) or self._handlers.get("*")
            if handler is None:
                pending = True
                executions.append(
                    _execution(
                        action,
                        status="pending",
                        message="No deterministic action handler is registered.",
                    )
                )
                continue

            try:
                message = handler(action)
            except Exception as error:  # noqa: BLE001 - execution boundary captures failures
                failed = True
                executions.append(
                    _execution(
                        action,
                        status="failed",
                        message="%s: %s" % (error.__class__.__name__, str(error)),
                    )
                )
                continue

            executions.append(
                _execution(
                    action,
                    status="completed",
                    message=str(message or "Action completed."),
                )
            )

        status = "failed" if failed else "pending" if pending else "completed"
        return _run(
            plan,
            tuple(executions),
            status,
            authoritative=plan.authoritative and status == "completed",
        )


def _execution(
    action: PlanningAction,
    *,
    status: str,
    message: str,
) -> ActionExecution:
    return ActionExecution(
        sequence=action.sequence,
        action_code=action.code,
        status=status,
        message=message,
        target_entities=action.target_entities,
        supporting_event_ids=action.supporting_event_ids,
    )


def _run(
    plan: ExecutionPlan,
    executions: Tuple[ActionExecution, ...],
    status: str,
    *,
    authoritative: bool,
) -> ExecutionRun:
    return ExecutionRun(
        mission=plan.mission,
        plan=plan,
        action_executions=executions,
        status=status,
        warnings=tuple(plan.warnings),
        supporting_event_ids=_supporting_event_ids(plan, executions),
        authoritative=authoritative,
    )


def _supporting_event_ids(
    plan: ExecutionPlan,
    executions: Tuple[ActionExecution, ...],
) -> Tuple[str, ...]:
    values: Iterable[str] = (
        event_id
        for collection in (
            tuple(plan.supporting_event_ids),
            tuple(
                event_id
                for execution in executions
                for event_id in execution.supporting_event_ids
            ),
        )
        for event_id in collection
    )
    return tuple(dict.fromkeys(value for value in values if value))


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
