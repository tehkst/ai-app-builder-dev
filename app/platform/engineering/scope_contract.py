from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


APPROVED_WORK_TYPES = {
    "platform_improvement",
    "customer_product",
    "bug_fix",
    "migration",
    "security",
    "performance",
    "documentation",
    "research",
    "operations",
}

APPROVED_DIVISIONS = {"platform", "product"}

SCOPE_GATE_STATES = [
    "DRAFT",
    "READY_FOR_SCOPE_APPROVAL",
    "SCOPE_APPROVED",
    "BUILD_PREVIEW_READY",
    "REVIEW_READY",
    "TEST_READY",
    "REPAIR_REQUIRED",
    "APPROVAL_READY",
    "MATERIALIZATION_APPROVED",
    "ROLLOUT_READY",
    "ROLLED_OUT",
]

PLATFORM_WORK_TYPES = {
    "platform_improvement",
    "migration",
    "security",
    "performance",
    "documentation",
    "research",
    "operations",
}


@dataclass(frozen=True)
class ScopeContractValidationIssue:
    field: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {"field": self.field, "reason": self.reason}


@dataclass
class ScopeContract:
    goal: str
    work_type: str
    division: str
    requested_capabilities: List[str]
    acceptance_criteria: List[str]
    test_plan: List[str]
    in_scope: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    affected_systems: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    approval_required_before_build: bool = True
    approval_required_before_materialization: bool = True
    rollout_target: str = "db_preview_only"
    rollback_plan_required: bool = True
    state: str = "DRAFT"
    scope_contract_id: str = field(default_factory=lambda: "scope_contract_" + uuid.uuid4().hex)

    def validate(self) -> List[ScopeContractValidationIssue]:
        issues: List[ScopeContractValidationIssue] = []

        if not self.goal.strip():
            issues.append(ScopeContractValidationIssue("goal", "goal_required"))
        if self.work_type not in APPROVED_WORK_TYPES:
            issues.append(ScopeContractValidationIssue("work_type", "unknown_work_type"))
        if self.division not in APPROVED_DIVISIONS:
            issues.append(ScopeContractValidationIssue("division", "unknown_division"))
        if not self.requested_capabilities:
            issues.append(ScopeContractValidationIssue("requested_capabilities", "at_least_one_capability_required"))
        if not self.acceptance_criteria:
            issues.append(ScopeContractValidationIssue("acceptance_criteria", "at_least_one_acceptance_criterion_required"))
        if not self.test_plan:
            issues.append(ScopeContractValidationIssue("test_plan", "at_least_one_test_step_required"))
        if not self.rollout_target.strip():
            issues.append(ScopeContractValidationIssue("rollout_target", "rollout_target_required"))
        if self.state not in SCOPE_GATE_STATES:
            issues.append(ScopeContractValidationIssue("state", "unknown_scope_gate_state"))
        if not self.approval_required_before_build:
            issues.append(ScopeContractValidationIssue("approval_required_before_build", "scope_approval_required_before_build"))
        if not self.approval_required_before_materialization:
            issues.append(ScopeContractValidationIssue("approval_required_before_materialization", "materialization_approval_required"))

        return issues

    def is_valid(self) -> bool:
        return not self.validate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope_contract_id": self.scope_contract_id,
            "goal": self.goal,
            "work_type": self.work_type,
            "division": self.division,
            "requested_capabilities": self.requested_capabilities,
            "in_scope": self.in_scope,
            "out_of_scope": self.out_of_scope,
            "acceptance_criteria": self.acceptance_criteria,
            "affected_systems": self.affected_systems,
            "risks": self.risks,
            "test_plan": self.test_plan,
            "approval_required_before_build": self.approval_required_before_build,
            "approval_required_before_materialization": self.approval_required_before_materialization,
            "rollout_target": self.rollout_target,
            "rollback_plan_required": self.rollback_plan_required,
            "state": self.state,
            "valid": self.is_valid(),
            "validation_issues": [issue.to_dict() for issue in self.validate()],
        }


def default_division_for_work_type(work_type: str) -> str:
    if work_type == "customer_product":
        return "product"
    return "platform"


def draft_scope_contract(
    *,
    goal: str,
    work_type: str,
    requested_capabilities: List[str],
    acceptance_criteria: List[str],
    test_plan: List[str],
    in_scope: List[str] = None,
    out_of_scope: List[str] = None,
    affected_systems: List[str] = None,
    risks: List[str] = None,
    rollout_target: str = "db_preview_only",
) -> ScopeContract:
    return ScopeContract(
        goal=goal,
        work_type=work_type,
        division=default_division_for_work_type(work_type),
        requested_capabilities=requested_capabilities,
        acceptance_criteria=acceptance_criteria,
        test_plan=test_plan,
        in_scope=in_scope or [],
        out_of_scope=out_of_scope or [],
        affected_systems=affected_systems or [],
        risks=risks or [],
        rollout_target=rollout_target,
    )
