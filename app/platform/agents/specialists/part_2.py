from __future__ import annotations

from typing import Any, Dict

from app.platform.services.app_generation_service import (
    repair_app_build_files,
    review_app_build_files,
)
from app.platform.agents.workflow_step_context import _goal, _dependency_output_for_step


_REVIEW_CHECKLIST = [
    "Validate architecture matches user goal",
    "Check security-sensitive operations",
    "Check database model consistency",
    "Check API route naming",
    "Check approval requirement for risky actions",
    "Check tests are defined before deployment",
    "Confirm generated artifacts remain DB-preview only before materialization approval",
]


def _reviewer_checklist_only(goal: str, message: str) -> Dict[str, Any]:
    return {
        "success": True,
        "agent_id": "reviewer_agent",
        "message": message,
        "goal": goal,
        "review_checklist": _REVIEW_CHECKLIST,
        "independent_review_performed": False,
        "next_recommended_task": "test_task",
    }


def reviewer_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    """Independently reviews the builder's generated files with a swapped-provider
    model, and - if it finds blocking issues - runs one bounded repair attempt
    with the builder's own provider before letting the build proceed.

    Falls back to the old decorative checklist-only behavior whenever there is
    nothing to review (no builder output) or the independent reviewer itself is
    unavailable, so a provider outage never blocks a build that would otherwise
    succeed.
    """
    goal = _goal(task)
    input_payload = task.get("input_payload") or {}

    from app.platform.runtime.review_settings import independent_review_enabled

    if not independent_review_enabled():
        return _reviewer_checklist_only(
            goal,
            "Reviewer Agent produced a review checklist (independent cross-model review is turned off in Settings).",
        )

    builder_output = _dependency_output_for_step(task, "builder")
    generated_files = builder_output.get("generated_files") or []
    builder_generation = (builder_output.get("implementation_plan") or {}).get("generation") or {}
    builder_provider = builder_generation.get("provider")

    if not generated_files or not builder_provider:
        return _reviewer_checklist_only(
            goal,
            "Reviewer Agent produced a review checklist (no generated files were available to independently review).",
        )

    review_provider = _other_provider(builder_provider)
    review = review_app_build_files(
        app_request=str(input_payload.get("app_request") or goal),
        scope_of_work_markdown=str(input_payload.get("scope_of_work_markdown") or ""),
        acceptance_criteria=input_payload.get("acceptance_criteria") or [],
        out_of_scope=input_payload.get("out_of_scope") or [],
        generated_files=generated_files,
        provider=review_provider,
    )

    if review is None:
        return _reviewer_checklist_only(
            goal,
            f"Reviewer Agent produced a review checklist (independent review via {review_provider} was unavailable).",
        )

    if review.get("approved"):
        return {
            "success": True,
            "agent_id": "reviewer_agent",
            "message": f"Reviewer Agent (independent review via {review.get('provider')}) approved the generated application with no blocking findings.",
            "goal": goal,
            "review_checklist": _REVIEW_CHECKLIST,
            "independent_review_performed": True,
            "independent_review": review,
            "next_recommended_task": "test_task",
        }

    repair = repair_app_build_files(
        app_request=str(input_payload.get("app_request") or goal),
        scope_of_work_markdown=str(input_payload.get("scope_of_work_markdown") or ""),
        acceptance_criteria=input_payload.get("acceptance_criteria") or [],
        out_of_scope=input_payload.get("out_of_scope") or [],
        previous_files=generated_files,
        review_findings=review.get("findings") or [],
        provider=builder_provider,
    )

    if not repair.get("success"):
        return {
            "success": False,
            "agent_id": "reviewer_agent",
            "message": (
                f"Reviewer Agent (independent review via {review.get('provider')}) found blocking issues "
                f"and the automatic repair attempt did not resolve them: {repair.get('blocked_reason')}"
            ),
            "goal": goal,
            "review_checklist": _REVIEW_CHECKLIST,
            "independent_review_performed": True,
            "independent_review": review,
            "repair_attempted": True,
            "repair_blocked_reason": repair.get("blocked_reason"),
            "next_recommended_task": None,
        }

    repaired_files = repair.get("files") or []
    return {
        "success": True,
        "agent_id": "reviewer_agent",
        "message": (
            f"Reviewer Agent (independent review via {review.get('provider')}) found "
            f"{len(review.get('findings') or [])} issue(s) and repaired them via {builder_provider}."
        ),
        "goal": goal,
        "review_checklist": _REVIEW_CHECKLIST,
        "independent_review_performed": True,
        "independent_review": review,
        "repair_attempted": True,
        "repair_result": {
            "app_name": repair.get("app_name"),
            "summary": repair.get("summary"),
            "generated_file_count": len(repaired_files),
            "generation": repair.get("generation") or {},
        },
        "generated_files": repaired_files,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
        "materialization_performed": False,
        "next_recommended_task": "test_task",
    }


def code_steward_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "code_steward_agent",
        "message": "Code Steward Agent produced a modularity and refactor guard report.",
        "goal": goal,
        "modularity_report": {
            "max_file_size_policy": "Keep platform modules small and split files before they become orchestration bottlenecks.",
            "checks": [
                "Detect oversized modules",
                "Detect duplicated routing or registry logic",
                "Recommend module splits by responsibility",
                "Preserve manifest-driven boundaries",
                "Prevent runtime changes from bypassing validation gates",
            ],
            "writes_code": False,
            "safe_mode": True,
        },
    }


def validation_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "test_agent",
        "message": "Test Agent V1 produced a validation plan.",
        "goal": goal,
        "validation_plan": {
            "compile_checks": True,
            "release_gate": "fast",
            "api_smoke_tests": True,
            "generated_artifact_contract_checks": True,
            "manual_approval_required_before_deployment": True,
        },
    }

