from __future__ import annotations

from typing import Any, Dict

from app.platform.engineering.director import classify_engineering_request, draft_scope_from_request
from app.platform.engineering.scope_contract import ScopeContract


def build_scope_gate_result(
    *,
    request_text: str,
    scope_approved: bool = False,
) -> Dict[str, Any]:
    classification = classify_engineering_request(request_text)
    scope_contract = draft_scope_from_request(request_text)
    validation_issues = scope_contract.validate()
    scope_valid = not validation_issues
    build_allowed = scope_valid and scope_approved

    return {
        "success": build_allowed,
        "status": "scope_approved" if build_allowed else "scope_approval_required",
        "classification": classification.to_dict(),
        "scope_contract": scope_contract.to_dict(),
        "scope_contract_valid": scope_valid,
        "scope_approved": scope_approved,
        "scope_before_build_enforced": True,
        "build_allowed": build_allowed,
        "build_started": False,
        "materialization_performed": False,
        "approval_required_before_build": True,
        "approval_required_before_materialization": True,
    }


def require_scope_approval(
    *,
    request_text: str,
    scope_approved: bool = False,
) -> Dict[str, Any]:
    """Return an explicit gate result before Planner/Builder execution begins."""

    return build_scope_gate_result(
        request_text=request_text,
        scope_approved=scope_approved,
    )


def scope_contract_from_gate_result(gate_result: Dict[str, Any]) -> ScopeContract:
    contract_data = gate_result.get("scope_contract") or {}
    return ScopeContract(
        goal=str(contract_data.get("goal") or ""),
        work_type=str(contract_data.get("work_type") or "research"),
        division=str(contract_data.get("division") or "platform"),
        requested_capabilities=list(contract_data.get("requested_capabilities") or []),
        acceptance_criteria=list(contract_data.get("acceptance_criteria") or []),
        test_plan=list(contract_data.get("test_plan") or []),
        in_scope=list(contract_data.get("in_scope") or []),
        out_of_scope=list(contract_data.get("out_of_scope") or []),
        affected_systems=list(contract_data.get("affected_systems") or []),
        risks=list(contract_data.get("risks") or []),
        approval_required_before_build=bool(contract_data.get("approval_required_before_build", True)),
        approval_required_before_materialization=bool(contract_data.get("approval_required_before_materialization", True)),
        rollout_target=str(contract_data.get("rollout_target") or "db_preview_only"),
        rollback_plan_required=bool(contract_data.get("rollback_plan_required", True)),
        state=str(contract_data.get("state") or "DRAFT"),
        scope_contract_id=str(contract_data.get("scope_contract_id") or ""),
    )
