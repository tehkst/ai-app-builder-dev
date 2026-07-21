from __future__ import annotations

from app.platform.events.company_brain_models import CompanyBrainEntity
from app.platform.events.company_brain_principle_engine import CompanyBrainPrincipleEngine
from app.platform.events.company_brain_principle_models import (
    POLICY_ALLOW,
    POLICY_DENY,
    POLICY_MODIFY,
    POLICY_REQUIRE_APPROVAL,
    GovernedPrinciple,
)
from app.platform.events.company_brain_reasoning_models import (
    ExecutionPlan,
    PlanningAction,
    ReasoningFinding,
)


def _plan(
    *,
    code: str = "VERIFY_MISSION_OUTCOME",
    priority: str = "normal",
    evidence: tuple[str, ...] = ("event-1",),
    authoritative: bool = True,
    blocked: bool = False,
) -> ExecutionPlan:
    mission = CompanyBrainEntity("PlatformMission", "mission-1")
    blocker = (
        ReasoningFinding(
            code="MISSION_BLOCKED",
            title="Mission blocked",
            description="Resolve the blocker.",
            severity="error",
            related_entities=(mission,),
        ),
    ) if blocked else ()
    return ExecutionPlan(
        mission=mission,
        actions=(
            PlanningAction(
                sequence=1,
                code=code,
                title="Action",
                description="Perform a governed action.",
                priority=priority,
                target_entities=(mission,),
                supporting_event_ids=evidence,
            ),
        ),
        blockers=blocker,
        supporting_event_ids=evidence,
        authoritative=authoritative,
    )


def _check_allow() -> None:
    evaluation = CompanyBrainPrincipleEngine().evaluate_plan(_plan())
    assert evaluation.decision == POLICY_ALLOW
    assert evaluation.authoritative is True
    assert evaluation.executable is True
    assert evaluation.approval_required is False
    assert evaluation.supporting_event_ids == ("event-1",)
    assert evaluation.as_dict()["decision"] == POLICY_ALLOW


def _check_missing_evidence_requires_approval() -> None:
    evaluation = CompanyBrainPrincipleEngine().evaluate_plan(_plan(evidence=()))
    assert evaluation.decision == POLICY_REQUIRE_APPROVAL
    assert evaluation.approval_required is True
    assert evaluation.executable is False
    assert evaluation.findings[0].principle_code == "EVIDENCE_BEFORE_EXECUTION"


def _check_critical_requires_approval() -> None:
    evaluation = CompanyBrainPrincipleEngine().evaluate_plan(
        _plan(priority="critical")
    )
    assert evaluation.decision == POLICY_REQUIRE_APPROVAL
    assert any(
        finding.principle_code == "HUMAN_APPROVAL_FOR_CRITICAL_ACTIONS"
        for finding in evaluation.findings
    )


def _check_destructive_requires_approval() -> None:
    evaluation = CompanyBrainPrincipleEngine().evaluate_plan(
        _plan(code="DELETE_PRODUCTION_RESOURCE")
    )
    assert evaluation.decision == POLICY_REQUIRE_APPROVAL
    assert any(
        finding.principle_code == "HUMAN_APPROVAL_FOR_DESTRUCTIVE_ACTIONS"
        for finding in evaluation.findings
    )


def _check_blocked_plan_is_denied() -> None:
    evaluation = CompanyBrainPrincipleEngine().evaluate_plan(
        _plan(authoritative=False, blocked=True)
    )
    assert evaluation.decision == POLICY_DENY
    assert evaluation.authoritative is False
    assert evaluation.executable is False


def _check_custom_modify_and_precedence() -> None:
    modify = GovernedPrinciple(
        code="MODIFY_VERIFY",
        title="Modify verification",
        statement="Verification must use the governed adapter.",
        effect=POLICY_MODIFY,
        action_codes=("VERIFY_MISSION_OUTCOME",),
    )
    evaluation = CompanyBrainPrincipleEngine((modify,)).evaluate_plan(_plan())
    assert evaluation.decision == POLICY_MODIFY
    assert evaluation.executable is True

    deny = GovernedPrinciple(
        code="DENY_VERIFY",
        title="Deny verification",
        statement="Verification is denied.",
        effect=POLICY_DENY,
        action_codes=("VERIFY_MISSION_OUTCOME",),
    )
    evaluation = CompanyBrainPrincipleEngine((modify, deny)).evaluate_plan(_plan())
    assert evaluation.decision == POLICY_DENY


def _check_non_authoritative_principle_is_ignored() -> None:
    principle = GovernedPrinciple(
        code="UNAPPROVED_RULE",
        title="Unapproved rule",
        statement="This rule is not governed.",
        effect=POLICY_DENY,
        authoritative=False,
    )
    evaluation = CompanyBrainPrincipleEngine((principle,)).evaluate_plan(_plan())
    assert evaluation.decision == POLICY_ALLOW
    assert evaluation.authoritative is True
    assert evaluation.warnings == (
        "Principle UNAPPROVED_RULE is not authoritative and was ignored.",
    )


def _check_validation() -> None:
    try:
        CompanyBrainPrincipleEngine().evaluate_plan(None)  # type: ignore[arg-type]
    except TypeError as error:
        assert str(error) == "plan must be an ExecutionPlan"
    else:
        raise AssertionError("invalid plan must fail")

    duplicate = GovernedPrinciple(
        code="DUPLICATE",
        title="Duplicate",
        statement="Duplicate.",
        effect=POLICY_ALLOW,
    )
    try:
        CompanyBrainPrincipleEngine((duplicate, duplicate))
    except ValueError as error:
        assert str(error) == "duplicate principle code: DUPLICATE"
    else:
        raise AssertionError("duplicate principles must fail")

    invalid = GovernedPrinciple(
        code="INVALID",
        title="Invalid",
        statement="Invalid.",
        effect="unknown",
    )
    try:
        CompanyBrainPrincipleEngine((invalid,))
    except ValueError as error:
        assert str(error) == "unsupported principle effect: unknown"
    else:
        raise AssertionError("unsupported effects must fail")


def main() -> None:
    _check_allow()
    _check_missing_evidence_requires_approval()
    _check_critical_requires_approval()
    _check_destructive_requires_approval()
    _check_blocked_plan_is_denied()
    _check_custom_modify_and_precedence()
    _check_non_authoritative_principle_is_ignored()
    _check_validation()
    print("company brain principle engine: PASS")


if __name__ == "__main__":
    main()
