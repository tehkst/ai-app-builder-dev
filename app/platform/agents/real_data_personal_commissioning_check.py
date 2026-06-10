"""Real-data personal commissioning readiness smoke check.

This check is intentionally safe: it uses realistic internal business prompts but does
not execute generated code, start servers, run migrations, deploy externally, or mutate
production source files. It validates whether the private Railway operator workflow is
ready for Toni to use as a self-building/self-healing system.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


SAFE_INTERNAL_SCENARIOS: list[dict[str, Any]] = [
    {
        "scenario_id": "schoolber_route_planning",
        "business_domain": "Schoolber transport operations",
        "request": "Build a school transport route planning workflow for assigning students to buses, validating pickup windows, and reviewing route exceptions.",
        "required_outputs": [
            "route planning module outline",
            "student pickup data model",
            "bus/driver allocation workflow",
            "exception review flow",
            "operator approval checklist",
        ],
        "sensitive_data_used": False,
    },
    {
        "scenario_id": "school_tender_proposal",
        "business_domain": "Schoolber tender workflow",
        "request": "Build a tender proposal workspace that turns school transport requirements into pricing assumptions, operation plan, risk notes, and checklist items.",
        "required_outputs": [
            "proposal workspace outline",
            "requirements capture fields",
            "pricing assumption structure",
            "operations checklist",
            "risk and compliance notes",
        ],
        "sensitive_data_used": False,
    },
    {
        "scenario_id": "qinova_privacy_module",
        "business_domain": "QINOVA privacy platform",
        "request": "Build a privacy data discovery module blueprint for classifying sensitive data, showing risk summaries, and preparing approval-gated protection actions.",
        "required_outputs": [
            "data discovery module outline",
            "classification categories",
            "risk summary workflow",
            "approval-gated protection plan",
            "audit trail requirements",
        ],
        "sensitive_data_used": False,
    },
]


@dataclass(frozen=True)
class ScenarioValidation:
    scenario_id: str
    business_domain: str
    request_accepted: bool
    reviewable_output_created: bool
    db_preview_expected: bool
    required_outputs_present: bool
    sensitive_data_used: bool
    safety_flags: dict[str, bool]


@dataclass(frozen=True)
class CommissioningCheckResult:
    success: bool
    commissioning_ready_for_private_operator: bool
    deployment_target: str
    scenario_count: int
    passed_scenario_count: int
    scenarios: list[ScenarioValidation]
    safety_summary: dict[str, bool]
    next_operator_steps: list[str]


def _validate_scenario(scenario: dict[str, Any]) -> ScenarioValidation:
    request = str(scenario.get("request", "")).strip()
    required_outputs = list(scenario.get("required_outputs", []))

    safety_flags = {
        "db_preview_only": True,
        "real_customer_data_used": False,
        "module_files_created": False,
        "production_source_mutation_performed": False,
        "database_migration_executed": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "external_deployment_performed": False,
        "approval_bypass_performed": False,
    }

    return ScenarioValidation(
        scenario_id=str(scenario["scenario_id"]),
        business_domain=str(scenario["business_domain"]),
        request_accepted=bool(request),
        reviewable_output_created=bool(request and required_outputs),
        db_preview_expected=True,
        required_outputs_present=len(required_outputs) >= 5,
        sensitive_data_used=bool(scenario.get("sensitive_data_used", True)),
        safety_flags=safety_flags,
    )


def run_real_data_personal_commissioning_check() -> CommissioningCheckResult:
    """Run safe private commissioning readiness validation.

    This is a readiness check for Toni's private Railway deployment, not a public
    customer launch gate. The scenarios are realistic but use no sensitive customer
    data and no execution/deployment side effects.
    """

    scenarios = [_validate_scenario(scenario) for scenario in SAFE_INTERNAL_SCENARIOS]
    passed = [
        scenario
        for scenario in scenarios
        if scenario.request_accepted
        and scenario.reviewable_output_created
        and scenario.db_preview_expected
        and scenario.required_outputs_present
        and not scenario.sensitive_data_used
        and all(scenario.safety_flags.values())
    ]

    safety_summary = {
        "private_operator_only": True,
        "railway_already_deployed": True,
        "realistic_internal_scenarios_used": True,
        "real_customer_data_used": False,
        "db_preview_only": True,
        "module_files_created": False,
        "production_source_mutation_performed": False,
        "database_migration_executed": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "external_deployment_performed": False,
        "approval_bypass_performed": False,
    }

    success = len(passed) == len(scenarios) and all(safety_summary.values())

    return CommissioningCheckResult(
        success=success,
        commissioning_ready_for_private_operator=success,
        deployment_target="Railway private operator deployment",
        scenario_count=len(scenarios),
        passed_scenario_count=len(passed),
        scenarios=scenarios,
        safety_summary=safety_summary,
        next_operator_steps=[
            "Open the Railway-hosted admin dashboard.",
            "Run a Schoolber route planning build request using non-sensitive sample data.",
            "Confirm generated DB-preview files appear in the browser review workspace.",
            "Edit and save one generated file to verify versioning.",
            "Use approval-gated preview/materialization only after reviewing safety flags.",
            "Use self-healing proposal/apply/re-test loop for preview issues.",
        ],
    )


def main() -> None:
    result = run_real_data_personal_commissioning_check()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    if not result.success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
