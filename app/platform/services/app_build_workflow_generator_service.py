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
    """Build the real app-build step chain, now routed through the management
    hierarchy (v2) rather than dispatching straight to a builder with no upstream
    delegation: CEO business sign-off -> architecture -> Engineering Manager
    buildability check -> CTO technical sign-off -> builder -> the three
    functional managers reviewing the same generated output in parallel, each
    through their own domain lens -> independent review -> Quality Manager
    release-readiness check -> validation planning. Any manager step that
    redirects or escalates (handler returns success=False) blocks everything
    that requires it, via the executor's existing dependency-blocking mechanism -
    no new blocking logic needed here, just the right requires_steps chain.
    """
    cleaned_request = _clean_app_request(app_request)
    resolved_workflow_name = workflow_name or f"Build App: {cleaned_request[:80]}"

    steps: List[Dict[str, Any]] = [
        {
            "step_id": "ceo_review",
            "title": "CEO Business Alignment Review",
            "description": (
                "Judge whether this build request is a sound business decision worth pursuing as scoped. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "ceo_task",
            "requires_steps": [],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "management_decision",
            },
        },
        {
            "step_id": "architecture",
            "title": "Create Application Architecture Plan",
            "description": (
                "Create a safe architecture plan for the requested app. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "architect_task",
            "requires_steps": ["ceo_review"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "architecture_plan",
            },
        },
        {
            "step_id": "engineering_manager_review",
            "title": "Engineering Manager Buildability Review",
            "description": (
                "Judge whether the architecture plan is concrete and buildable as written. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "engineering_manager_task",
            "requires_steps": ["architecture"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "management_decision",
            },
        },
        {
            "step_id": "cto_review",
            "title": "CTO Technical Soundness Review",
            "description": (
                "Judge whether the architecture plan is technically sound and strategically consistent. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "cto_task",
            "requires_steps": ["engineering_manager_review"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "management_decision",
            },
        },
        {
            "step_id": "builder",
            "title": "Generate Application Files",
            "description": (
                "Generate the complete application implementation for the approved scope. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "builder_task",
            "requires_steps": ["cto_review"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "generated_files",
                "scope_of_work_markdown": scope_of_work_markdown,
                "acceptance_criteria": acceptance_criteria or [],
                "out_of_scope": out_of_scope or [],
            },
        },
        {
            "step_id": "backend_manager_review",
            "title": "Backend Manager Review",
            "description": (
                "Judge the generated backend/API implementation for correctness and safety. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "backend_manager_task",
            "requires_steps": ["builder"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "management_decision",
            },
        },
        {
            "step_id": "frontend_manager_review",
            "title": "Frontend Manager Review",
            "description": (
                "Judge the generated frontend/UI implementation for quality and usability. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "frontend_manager_task",
            "requires_steps": ["builder"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "management_decision",
            },
        },
        {
            "step_id": "database_manager_review",
            "title": "Database Manager Review",
            "description": (
                "Judge the generated data model and schema for soundness. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "database_manager_task",
            "requires_steps": ["builder"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "management_decision",
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
            "requires_steps": ["backend_manager_review", "frontend_manager_review", "database_manager_review"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "review_checklist",
            },
        },
        {
            "step_id": "quality_manager_review",
            "title": "Quality Manager Release-Readiness Review",
            "description": (
                "Judge whether the review findings indicate the build is ready for validation and release. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "quality_manager_task",
            "requires_steps": ["review"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "management_decision",
            },
        },
        {
            "step_id": "test",
            "title": "Create Validation Plan",
            "description": (
                "Create a validation plan for the reviewed app build plan. "
                f"User app request: {cleaned_request}"
            ),
            "required_capability": "test_task",
            "requires_steps": ["quality_manager_review"],
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
