from __future__ import annotations

from typing import Iterable, Optional, Tuple

from app.platform.events.company_brain_evolution_models import (
    EVOLUTION_COMPLETE,
    EVOLUTION_CONTINUE,
    EVOLUTION_REPLAN,
    EVOLUTION_REQUIRE_APPROVAL,
    EVOLUTION_STOP,
    EvolutionCycle,
    ExecutionObservation,
)
from app.platform.events.company_brain_learning_engine import CompanyBrainLearningEngine
from app.platform.events.company_brain_mission_reasoning_engine import (
    CompanyBrainMissionReasoningEngine,
)
from app.platform.events.company_brain_planning_engine import CompanyBrainPlanningEngine
from app.platform.events.company_brain_principle_engine import CompanyBrainPrincipleEngine
from app.platform.events.company_brain_principle_models import (
    POLICY_DENY,
    POLICY_REQUIRE_APPROVAL,
)
from app.platform.events.company_brain_reasoning_models import ExecutionRun, ReasoningFinding


class CompanyBrainEvolutionEngine:
    """Close the governed observe-learn-reason-replan-policy loop.

    This orchestrator deliberately delegates learning, mission reasoning, planning,
    and policy evaluation to their existing engines. It neither reads durable events
    nor executes actions directly.
    """

    def __init__(
        self,
        learning_engine: Optional[CompanyBrainLearningEngine] = None,
        mission_reasoning_engine: Optional[CompanyBrainMissionReasoningEngine] = None,
        planning_engine: Optional[CompanyBrainPlanningEngine] = None,
        principle_engine: Optional[CompanyBrainPrincipleEngine] = None,
    ) -> None:
        self._learning_engine = learning_engine or CompanyBrainLearningEngine()
        self._mission_reasoning_engine = (
            mission_reasoning_engine or CompanyBrainMissionReasoningEngine()
        )
        self._planning_engine = planning_engine or CompanyBrainPlanningEngine()
        self._principle_engine = principle_engine or CompanyBrainPrincipleEngine()

    def evolve(self, run: ExecutionRun) -> EvolutionCycle:
        if not isinstance(run, ExecutionRun):
            raise TypeError("run must be an ExecutionRun")

        observation = _observe(run)
        learning = self._learning_engine.learn_from_execution(run)
        reasoning = self._mission_reasoning_engine.assess_mission(run.mission.entity_id)
        revised_plan = self._planning_engine.generate_execution_plan(run.mission.entity_id)
        policy = self._principle_engine.evaluate_plan(revised_plan)
        disposition, next_action = _disposition(
            run,
            observation,
            reasoning.authoritative,
            policy.decision,
            reasoning.next_best_action,
        )
        warnings = tuple(
            dict.fromkeys(
                tuple(run.warnings)
                + tuple(learning.warnings)
                + tuple(reasoning.warnings)
                + tuple(revised_plan.warnings)
                + tuple(policy.warnings)
            )
        )
        authoritative = (
            run.authoritative
            and observation.authoritative
            and reasoning.authoritative
            and revised_plan.authoritative
            and policy.authoritative
        )
        return EvolutionCycle(
            run=run,
            observation=observation,
            learning=learning,
            reasoning=reasoning,
            revised_plan=revised_plan,
            policy=policy,
            disposition=disposition,
            next_action=next_action,
            warnings=warnings,
            supporting_event_ids=_supporting_event_ids(
                run,
                observation,
                learning,
                reasoning,
                revised_plan,
                policy,
            ),
            authoritative=authoritative,
        )


def _observe(run: ExecutionRun) -> ExecutionObservation:
    expected = tuple(action.code for action in sorted(run.plan.actions, key=lambda item: item.sequence))
    executions = tuple(sorted(run.action_executions, key=lambda item: item.sequence))
    expected_set = set(expected)
    observed_codes = {item.action_code for item in executions}
    missing = tuple(code for code in expected if code not in observed_codes)

    def codes(status: str) -> Tuple[str, ...]:
        return tuple(item.action_code for item in executions if item.status == status)

    unexpected = tuple(
        item.action_code for item in executions if item.action_code not in expected_set
    )
    findings = []
    if missing:
        findings.append(
            ReasoningFinding(
                code="EXPECTED_ACTIONS_NOT_OBSERVED",
                title="Expected actions were not observed",
                description="No execution outcome was recorded for: %s." % ", ".join(missing),
                severity="warning",
                supporting_event_ids=tuple(run.supporting_event_ids),
                related_entities=(run.mission,),
            )
        )
    if unexpected:
        findings.append(
            ReasoningFinding(
                code="UNEXPECTED_ACTIONS_OBSERVED",
                title="Unexpected actions were observed",
                description="Execution outcomes were recorded outside the governed plan: %s."
                % ", ".join(unexpected),
                severity="error",
                supporting_event_ids=tuple(run.supporting_event_ids),
                related_entities=(run.mission,),
            )
        )
    failed = codes("failed")
    blocked = codes("blocked")
    if failed or blocked:
        findings.append(
            ReasoningFinding(
                code="EXECUTION_DIVERGED_FROM_EXPECTATION",
                title="Execution diverged from the expected outcome",
                description="One or more governed actions failed or became blocked.",
                severity="error",
                supporting_event_ids=tuple(run.supporting_event_ids),
                related_entities=(run.mission,),
            )
        )
    evidence = tuple(
        dict.fromkeys(
            event_id
            for collection in (
                tuple(run.supporting_event_ids),
                tuple(
                    event_id
                    for item in executions
                    for event_id in item.supporting_event_ids
                ),
            )
            for event_id in collection
            if event_id
        )
    )
    return ExecutionObservation(
        expected_actions=expected,
        completed_actions=codes("completed"),
        failed_actions=failed,
        blocked_actions=blocked,
        pending_actions=tuple(dict.fromkeys(codes("pending") + missing)),
        skipped_actions=codes("skipped"),
        unexpected_actions=unexpected,
        findings=tuple(sorted(findings, key=lambda item: item.code)),
        supporting_event_ids=evidence,
        authoritative=run.authoritative and bool(evidence) and not unexpected,
    )


def _disposition(
    run: ExecutionRun,
    observation: ExecutionObservation,
    reasoning_authoritative: bool,
    policy_decision: str,
    reasoning_next_action: str,
) -> Tuple[str, str]:
    if policy_decision == POLICY_DENY:
        return EVOLUTION_STOP, "Stop and resolve the governed policy denial."
    if policy_decision == POLICY_REQUIRE_APPROVAL:
        return EVOLUTION_REQUIRE_APPROVAL, "Obtain human approval before continuing."
    if observation.unexpected_actions:
        return EVOLUTION_STOP, "Investigate actions executed outside the governed plan."
    if observation.failed_actions or observation.blocked_actions or observation.skipped_actions:
        return EVOLUTION_REPLAN, reasoning_next_action or "Generate a revised governed plan."
    if observation.pending_actions or run.status in {"pending", "running"}:
        return EVOLUTION_CONTINUE, "Continue the remaining governed actions."
    complete = (
        run.status == "completed"
        and set(observation.completed_actions) == set(observation.expected_actions)
        and reasoning_authoritative
    )
    if complete:
        return EVOLUTION_COMPLETE, "Mission execution matches the governed plan."
    return EVOLUTION_REPLAN, reasoning_next_action or "Reassess and replan the mission."


def _supporting_event_ids(run, observation, learning, reasoning, revised_plan, policy) -> Tuple[str, ...]:
    collections: Iterable[Tuple[str, ...]] = (
        tuple(run.supporting_event_ids),
        tuple(observation.supporting_event_ids),
        tuple(learning.supporting_event_ids),
        tuple(reasoning.supporting_event_ids),
        tuple(revised_plan.supporting_event_ids),
        tuple(policy.supporting_event_ids),
    )
    return tuple(
        dict.fromkeys(
            event_id
            for collection in collections
            for event_id in collection
            if event_id
        )
    )
