from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_APP_BUILD_WORKFLOW_VERSION = "v2"


def _clean_app_request(app_request: str) -> str:
    cleaned = " ".join((app_request or "").strip().split())
    if not cleaned:
        raise ValueError("app_request is required to generate an app build workflow.")
    return cleaned


_MAX_SCOPE_CHARS_IN_DESCRIPTION = 6000


def _describe(instruction: str, cleaned_request: str, scope_of_work_markdown: str) -> str:
    """Build a step's real description text.

    Review/decision steps (CEO, CTO, engineering/backend/frontend/database
    managers, reviewer, quality manager) previously only received the terse
    original app_request one-liner, never the actual drafted-and-approved scope
    of work the founder can see and approved - so a reviewer judging "business
    alignment" or "buildability" had nothing concrete to evaluate against and
    would reasonably call the request too vague. Include the real approved scope
    (capped, not the whole thing unbounded) whenever one exists.
    """
    parts = [instruction, f"User app request: {cleaned_request}"]
    if scope_of_work_markdown.strip():
        parts.append(
            "Approved scope of work:\n" + scope_of_work_markdown.strip()[:_MAX_SCOPE_CHARS_IN_DESCRIPTION]
        )
    return " ".join(parts[:2]) + ("\n\n" + parts[2] if len(parts) > 2 else "")


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
            "description": _describe(
                "Judge whether this build request is a sound business decision worth pursuing as scoped.",
                cleaned_request, scope_of_work_markdown,
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
            "description": _describe(
                "Create a safe architecture plan for the requested app.",
                cleaned_request, scope_of_work_markdown,
            ),
            "required_capability": "architect_task",
            "requires_steps": ["ceo_review"],
            "input": {
                "app_request": cleaned_request,
                "expected_output": "architecture_plan",
                "scope_of_work_markdown": scope_of_work_markdown,
                "acceptance_criteria": acceptance_criteria or [],
                "out_of_scope": out_of_scope or [],
            },
        },
        {
            "step_id": "engineering_manager_review",
            "title": "Engineering Manager Buildability Review",
            "description": _describe(
                "Judge whether the architecture plan is concrete and buildable as written.",
                cleaned_request, scope_of_work_markdown,
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
            "description": _describe(
                "Judge whether the architecture plan is technically sound and strategically consistent.",
                cleaned_request, scope_of_work_markdown,
            ),
            "required_capability": "cto_task",
            # Both are real dependencies, not just engineering_manager_review: the
            # CTO's own reviewed_step_id (management_agents/handlers.py's
            # cto_agent_handler) is "architecture", but _dependency_output_for_step
            # only ever exposes a step's DIRECT requires_steps entries in its
            # workflow_context - "architecture" being only a transitive dependency
            # (via engineering_manager_review) meant the CTO never actually received
            # the architecture artifact at all and escalated with "No architecture
            # plan artifact was provided for review" on every real build that got
            # this far - a real, reproduced bug, distinct from (and only reachable
            # after fixing) the architect_agent placeholder bug.
            "requires_steps": ["engineering_manager_review", "architecture"],
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
            "description": _describe(
                "Judge the generated backend/API implementation for correctness and safety.",
                cleaned_request, scope_of_work_markdown,
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
            "description": _describe(
                "Judge the generated frontend/UI implementation for quality and usability.",
                cleaned_request, scope_of_work_markdown,
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
            "description": _describe(
                "Judge the generated data model and schema for soundness.",
                cleaned_request, scope_of_work_markdown,
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
            "description": _describe(
                "Review the implementation plan for correctness, safety, and approval needs.",
                cleaned_request, scope_of_work_markdown,
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
            "description": _describe(
                "Judge whether the review findings indicate the build is ready for validation and release.",
                cleaned_request, scope_of_work_markdown,
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
            "description": _describe(
                "Create a validation plan for the reviewed app build plan.",
                cleaned_request, scope_of_work_markdown,
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
