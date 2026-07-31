from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_APP_BUILD_WORKFLOW_VERSION = "v2"


def _clean_app_request(app_request: str) -> str:
    cleaned = " ".join((app_request or "").strip().split())
    if not cleaned:
        raise ValueError("app_request is required to generate an app build workflow.")
    return cleaned


def generate_app_build_workflow(
    *,
    app_request: str,
    workflow_name: Optional[str] = None,
    scope_of_work_markdown: str = "",
    acceptance_criteria: Optional[List[str]] = None,
    out_of_scope: Optional[List[str]] = None,
) -> Dict[str, Any]:
    cleaned_request = _clean_app_request(app_request)
    resolved_workflow_name = workflow_name or f"Build App: {cleaned_request[:80]}"

    steps: List[Dict[str, Any]] = [
        {
            "step_id": "ceo",
            "title": "Evaluate Founder Request",
            "description": (
                "Decide whether this app request is worth building - business value, scope, "
                f"and risk - before any technical work starts. User app request: {cleaned_request}"
            ),
            "required_capability": "ceo_task",
            "requires_steps": [],
            "input": {"app_request": cleaned_request, "expected_output": "management_decision"},
        },
        {
            "step_id": "architecture",
            "title": "Create Application Architecture Plan",
            "description": (
                "Create a safe architecture plan for the requested app. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "architect_task",
            "requires_steps": ["ceo"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "architecture_plan",
            },
        },
        {
            "step_id": "cto",
            "title": "Evaluate Architecture Plan",
            "description": (
                "Evaluate the technical architecture plan for soundness, risk, and alignment "
                f"with the founder's stated goal. User app request: {cleaned_request}"
            ),
            "required_capability": "cto_task",
            "requires_steps": ["architecture"],
            "input": {"app_request": cleaned_request, "expected_output": "management_decision"},
        },
        {
            "step_id": "engineering_manager",
            "title": "Evaluate Execution Readiness",
            "description": (
                "Evaluate whether the CTO's approved technical decision can be cleanly divided "
                f"across backend, frontend, and database ownership. User app request: {cleaned_request}"
            ),
            "required_capability": "engineering_manager_task",
            "requires_steps": ["cto"],
            "input": {"app_request": cleaned_request, "expected_output": "management_decision"},
        },
        {
            "step_id": "backend_manager",
            "title": "Evaluate Backend Soundness",
            "description": (
                "Evaluate the architecture plan for backend, API, and business-logic soundness. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "backend_manager_task",
            "requires_steps": ["engineering_manager"],
            "input": {"app_request": cleaned_request, "expected_output": "management_decision"},
        },
        {
            "step_id": "frontend_manager",
            "title": "Evaluate Frontend Soundness",
            "description": (
                "Evaluate the architecture plan for frontend, UX, and interaction soundness. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "frontend_manager_task",
            "requires_steps": ["engineering_manager"],
            "input": {"app_request": cleaned_request, "expected_output": "management_decision"},
        },
        {
            "step_id": "database_manager",
            "title": "Evaluate Data Model Soundness",
            "description": (
                "Evaluate the architecture plan for data-model, schema, and persistence "
                f"soundness. User app request: {cleaned_request}"
            ),
            "required_capability": "database_manager_task",
            "requires_steps": ["engineering_manager"],
            "input": {"app_request": cleaned_request, "expected_output": "management_decision"},
        },
        {
            "step_id": "builder",
            "title": "Generate Application Files",
            "description": (
                "Generate the complete application implementation for the approved scope. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "builder_task",
            "requires_steps": ["backend_manager", "frontend_manager", "database_manager"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "generated_files",
                "scope_of_work_markdown": scope_of_work_markdown,
                "acceptance_criteria": acceptance_criteria or [],
                "out_of_scope": out_of_scope or [],
            },
        },
        {
            "step_id": "review",
            "title": "Review Implementation Plan",
            "description": (
                "Review the implementation plan for correctness, safety, and approval needs. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "reviewer_task",
            "requires_steps": ["builder"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "review_checklist",
            },
        },
        {
            "step_id": "quality_manager",
            "title": "Evaluate Release Readiness",
            "description": (
                "Evaluate the independent code review's findings as the final quality gate "
                f"before a validation plan is created. User app request: {cleaned_request}"
            ),
            "required_capability": "quality_manager_task",
            "requires_steps": ["review"],
            "input": {"app_request": cleaned_request, "expected_output": "management_decision"},
        },
        {
            "step_id": "test",
            "title": "Create Validation Plan",
            "description": (
                "Create a validation plan for the reviewed app build plan. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "test_task",
            "requires_steps": ["quality_manager"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "validation_plan",
            },
        },
    ]

    return {
        "success": True,
        "workflow_version": DEFAULT_APP_BUILD_WORKFLOW_VERSION,
        "workflow_name": resolved_workflow_name,
        "app_request": cleaned_request,
        "step_count": len(steps),
        "steps": steps,
    }
