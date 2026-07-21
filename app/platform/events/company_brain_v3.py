from __future__ import annotations

from typing import Iterable, Mapping, Optional, Tuple

from app.platform.events.company_brain_evolution_engine import CompanyBrainEvolutionEngine
from app.platform.events.company_brain_evolution_models import (
    EVOLUTION_COMPLETE,
    EVOLUTION_REQUIRE_APPROVAL,
    EVOLUTION_STOP,
)
from app.platform.events.company_brain_execution_engine import (
    ActionHandler,
    CompanyBrainExecutionEngine,
)
from app.platform.events.company_brain_mission_reasoning_engine import (
    CompanyBrainMissionReasoningEngine,
)
from app.platform.events.company_brain_planning_engine import CompanyBrainPlanningEngine
from app.platform.events.company_brain_principle_engine import CompanyBrainPrincipleEngine
from app.platform.events.company_brain_twin_engine import CompanyBrainTwinEngine
from app.platform.events.company_brain_v3_models import (
    MISSION_APPROVAL_REQUIRED,
    MISSION_BLOCKED,
    MISSION_COMPLETED,
    MISSION_FAILED,
    MISSION_PENDING,
    CompanyBrainV3Result,
)


class CompanyBrainV3:
    """Final governed facade over the existing Company Brain subsystems.

    This class owns lifecycle ordering only. Reasoning, planning, policy,
    execution, learning, evolution, and twin construction remain delegated to
    their existing authoritative engines.
    """

    def __init__(
        self,
        mission_reasoning_engine: Optional[CompanyBrainMissionReasoningEngine] = None,
        planning_engine: Optional[CompanyBrainPlanningEngine] = None,
        principle_engine: Optional[CompanyBrainPrincipleEngine] = None,
        execution_engine: Optional[CompanyBrainExecutionEngine] = None,
        evolution_engine: Optional[CompanyBrainEvolutionEngine] = None,
        twin_engine: Optional[CompanyBrainTwinEngine] = None,
        handlers: Optional[Mapping[str, ActionHandler]] = None,
    ) -> None:
        self._reasoning = mission_reasoning_engine or CompanyBrainMissionReasoningEngine()
        self._planning = planning_engine or CompanyBrainPlanningEngine()
        self._principles = principle_engine or CompanyBrainPrincipleEngine()
        self._execution = execution_engine or CompanyBrainExecutionEngine(
            planning_engine=self._planning,
            handlers=handlers,
        )
        self._evolution = evolution_engine or CompanyBrainEvolutionEngine(
            mission_reasoning_engine=self._reasoning,
            planning_engine=self._planning,
            principle_engine=self._principles,
        )
        self._twin = twin_engine or CompanyBrainTwinEngine()

    def run_mission(self, mission_id: str) -> CompanyBrainV3Result:
        normalized_id = _required(mission_id, "mission_id")
        reasoning = self._reasoning.assess_mission(normalized_id)
        plan = self._planning.generate_execution_plan(normalized_id)
        policy = self._principles.evaluate_plan(plan)
        twin = self._twin.build_snapshot(normalized_id)

        base_warnings = _warnings(
            reasoning.warnings,
            plan.warnings,
            policy.warnings,
            twin.warnings,
        )
        base_events = _event_ids(
            reasoning.supporting_event_ids,
            plan.supporting_event_ids,
            policy.supporting_event_ids,
            twin.supporting_event_ids,
        )

        if policy.approval_required:
            return CompanyBrainV3Result(
                mission_id=normalized_id,
                reasoning=reasoning,
                plan=plan,
                policy=policy,
                twin=twin,
                status=MISSION_APPROVAL_REQUIRED,
                next_action="Obtain governed human approval before execution.",
                warnings=base_warnings,
                supporting_event_ids=base_events,
                authoritative=_base_authoritative(reasoning, plan, policy, twin),
            )

        if not policy.executable:
            return CompanyBrainV3Result(
                mission_id=normalized_id,
                reasoning=reasoning,
                plan=plan,
                policy=policy,
                twin=twin,
                status=MISSION_BLOCKED,
                next_action=reasoning.next_best_action,
                warnings=base_warnings,
                supporting_event_ids=base_events,
                authoritative=False,
            )

        execution = self._execution.execute_plan(plan)
        evolution = self._evolution.evolve(execution)
        status = _status(execution.status, evolution.disposition)
        warnings = _warnings(base_warnings, execution.warnings, evolution.warnings)
        event_ids = _event_ids(
            base_events,
            execution.supporting_event_ids,
            evolution.supporting_event_ids,
        )
        authoritative = (
            _base_authoritative(reasoning, plan, policy, twin)
            and execution.authoritative
            and evolution.authoritative
        )
        return CompanyBrainV3Result(
            mission_id=normalized_id,
            reasoning=reasoning,
            plan=plan,
            policy=policy,
            twin=twin,
            execution=execution,
            evolution=evolution,
            status=status,
            next_action=evolution.next_action,
            warnings=warnings,
            supporting_event_ids=event_ids,
            authoritative=authoritative,
        )


def _status(execution_status: str, disposition: str) -> str:
    if disposition == EVOLUTION_REQUIRE_APPROVAL:
        return MISSION_APPROVAL_REQUIRED
    if disposition == EVOLUTION_COMPLETE:
        return MISSION_COMPLETED
    if disposition == EVOLUTION_STOP or execution_status in {"failed", "blocked"}:
        return MISSION_FAILED
    return MISSION_PENDING


def _base_authoritative(reasoning, plan, policy, twin) -> bool:
    return all(item.authoritative for item in (reasoning, plan, policy, twin))


def _warnings(*collections: Iterable[str]) -> Tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            warning
            for collection in collections
            for warning in collection
            if warning
        )
    )


def _event_ids(*collections: Iterable[str]) -> Tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            event_id
            for collection in collections
            for event_id in collection
            if event_id
        )
    )


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("%s is required" % name)
    return normalized
