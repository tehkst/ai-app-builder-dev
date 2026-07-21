from __future__ import annotations

from typing import Iterable, Sequence, Tuple

from app.platform.events.company_brain_principle_models import (
    POLICY_ALLOW,
    POLICY_DENY,
    POLICY_MODIFY,
    POLICY_REQUIRE_APPROVAL,
    GovernedPrinciple,
    PolicyEvaluation,
    PrincipleFinding,
)
from app.platform.events.company_brain_reasoning_models import ExecutionPlan, PlanningAction


_DECISION_ORDER = {
    POLICY_ALLOW: 0,
    POLICY_MODIFY: 1,
    POLICY_REQUIRE_APPROVAL: 2,
    POLICY_DENY: 3,
}

_DESTRUCTIVE_CODES = (
    "DELETE",
    "DROP",
    "DESTROY",
    "PURGE",
    "TERMINATE",
    "REMOVE_PRODUCTION",
)


class CompanyBrainPrincipleEngine:
    """Evaluate execution plans against explicit deterministic principles."""

    def __init__(
        self,
        principles: Sequence[GovernedPrinciple] | None = None,
    ) -> None:
        self._principles = tuple(principles or default_principles())
        _validate_principles(self._principles)

    @property
    def principles(self) -> Tuple[GovernedPrinciple, ...]:
        return self._principles

    def evaluate_plan(self, plan: ExecutionPlan) -> PolicyEvaluation:
        if not isinstance(plan, ExecutionPlan):
            raise TypeError("plan must be an ExecutionPlan")

        findings = []
        warnings = list(plan.warnings)

        if plan.blockers or not plan.authoritative:
            findings.append(
                PrincipleFinding(
                    principle_code="GOVERNED_PLAN_REQUIRED",
                    decision=POLICY_DENY,
                    explanation=(
                        "Execution is denied because the plan is blocked or is not authoritative."
                    ),
                    related_entities=(plan.mission,),
                    supporting_event_ids=tuple(plan.supporting_event_ids),
                    authoritative=True,
                )
            )

        for principle in self._principles:
            if not principle.authoritative:
                warnings.append(
                    "Principle %s is not authoritative and was ignored." % principle.code
                )
                continue

            for action in sorted(plan.actions, key=lambda item: item.sequence):
                if not _matches(principle, action):
                    continue

                if principle.requires_evidence and not action.supporting_event_ids:
                    findings.append(
                        _finding(
                            principle,
                            action,
                            POLICY_REQUIRE_APPROVAL,
                            "Human approval is required because the action has no supporting evidence.",
                        )
                    )
                    continue

                findings.append(
                    _finding(
                        principle,
                        action,
                        principle.effect,
                        principle.statement,
                    )
                )

        decision = _aggregate_decision(findings)
        authoritative = plan.authoritative and not plan.blockers and all(
            finding.authoritative for finding in findings
        )
        if not findings and authoritative:
            decision = POLICY_ALLOW

        return PolicyEvaluation(
            plan=plan,
            decision=decision,
            findings=tuple(findings),
            warnings=tuple(dict.fromkeys(warnings)),
            supporting_event_ids=_supporting_event_ids(plan, findings),
            authoritative=authoritative,
        )


def default_principles() -> Tuple[GovernedPrinciple, ...]:
    return (
        GovernedPrinciple(
            code="EVIDENCE_BEFORE_EXECUTION",
            title="Require evidence",
            statement="Every executable action must be supported by governed evidence.",
            effect=POLICY_ALLOW,
            requires_evidence=True,
        ),
        GovernedPrinciple(
            code="HUMAN_APPROVAL_FOR_CRITICAL_ACTIONS",
            title="Approve critical actions",
            statement="Critical actions require explicit human approval before execution.",
            effect=POLICY_REQUIRE_APPROVAL,
            priorities=("critical",),
        ),
        GovernedPrinciple(
            code="HUMAN_APPROVAL_FOR_DESTRUCTIVE_ACTIONS",
            title="Approve destructive actions",
            statement="Destructive actions require explicit human approval before execution.",
            effect=POLICY_REQUIRE_APPROVAL,
            action_codes=_DESTRUCTIVE_CODES,
        ),
    )


def _matches(principle: GovernedPrinciple, action: PlanningAction) -> bool:
    code_match = not principle.action_codes or any(
        token == action.code or token in action.code for token in principle.action_codes
    )
    priority_match = not principle.priorities or action.priority in principle.priorities
    return code_match and priority_match


def _finding(
    principle: GovernedPrinciple,
    action: PlanningAction,
    decision: str,
    explanation: str,
) -> PrincipleFinding:
    return PrincipleFinding(
        principle_code=principle.code,
        decision=decision,
        explanation=explanation,
        action=action,
        related_entities=action.target_entities,
        supporting_event_ids=action.supporting_event_ids,
        authoritative=principle.authoritative,
    )


def _aggregate_decision(findings: Sequence[PrincipleFinding]) -> str:
    if not findings:
        return POLICY_DENY
    return max(
        (finding.decision for finding in findings),
        key=lambda value: _DECISION_ORDER[value],
    )


def _supporting_event_ids(
    plan: ExecutionPlan,
    findings: Sequence[PrincipleFinding],
) -> Tuple[str, ...]:
    values: Iterable[str] = (
        event_id
        for collection in (
            tuple(plan.supporting_event_ids),
            tuple(
                event_id
                for finding in findings
                for event_id in finding.supporting_event_ids
            ),
        )
        for event_id in collection
    )
    return tuple(dict.fromkeys(value for value in values if value))


def _validate_principles(principles: Sequence[GovernedPrinciple]) -> None:
    seen = set()
    for principle in principles:
        if not isinstance(principle, GovernedPrinciple):
            raise TypeError("principles must contain GovernedPrinciple values")
        if not principle.code.strip():
            raise ValueError("principle code is required")
        if principle.code in seen:
            raise ValueError("duplicate principle code: %s" % principle.code)
        if principle.effect not in _DECISION_ORDER:
            raise ValueError("unsupported principle effect: %s" % principle.effect)
        seen.add(principle.code)
