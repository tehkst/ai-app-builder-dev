from __future__ import annotations

from typing import Any, Dict

from app.platform.agents.management_agents.core import invoke_management_review


def ceo_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return invoke_management_review(
        agent_id="ceo_agent",
        role_title="CEO Agent",
        role_description=(
            "Evaluates whether a requested build aligns with business goals, founder intent, and "
            "overall product direction."
        ),
        task=task,
        reviewed_step_id=None,
        focus_instructions=(
            "As CEO, judge whether this build request is a sound business/product decision worth "
            "pursuing as scoped - not whether it is technically correct (that is CTO/engineering's job). "
            "Consider value to the business, fit with the platform's direction, and whether the scope is "
            "reasonable for what was asked."
        ),
    )


def cto_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return invoke_management_review(
        agent_id="cto_agent",
        role_title="CTO Agent",
        role_description=(
            "Evaluates architecture decisions for technical soundness, scalability, and strategic "
            "engineering direction."
        ),
        task=task,
        reviewed_step_id="architecture",
        focus_instructions=(
            "As CTO, judge whether the proposed architecture plan is technically sound, appropriately "
            "scoped, and consistent with good engineering practice - not whether the business case is "
            "worth pursuing (the CEO's job) and not line-by-line implementation detail (the Engineering "
            "Manager's job)."
        ),
    )


def engineering_manager_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return invoke_management_review(
        agent_id="engineering_manager_agent",
        role_title="Engineering Manager Agent",
        role_description=(
            "Evaluates whether an approved architecture plan is buildable, correctly scoped, and ready "
            "to hand to the build team."
        ),
        task=task,
        reviewed_step_id="architecture",
        focus_instructions=(
            "As Engineering Manager, judge whether the architecture plan is concrete and buildable as "
            "written - are integration contracts, affected files, and constraints clear enough for a "
            "builder to act on without guessing? Redirect if the plan is too vague or missing needed "
            "detail; do not re-litigate the CTO's strategic/technical direction."
        ),
    )


def backend_manager_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return invoke_management_review(
        agent_id="backend_manager_agent",
        role_title="Backend Manager Agent",
        role_description="Evaluates the generated backend/API implementation for correctness and soundness.",
        task=task,
        reviewed_step_id="builder",
        focus_instructions=(
            "As Backend Manager, review only the backend/API/service-layer portions of the generated "
            "files and implementation plan. Judge whether the backend implementation is sound, safe, "
            "and matches the approved scope. Ignore frontend/UI and database-schema concerns - those "
            "belong to the Frontend and Database Managers."
        ),
    )


def frontend_manager_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return invoke_management_review(
        agent_id="frontend_manager_agent",
        role_title="Frontend Manager Agent",
        role_description="Evaluates the generated frontend/UI implementation for quality and usability.",
        task=task,
        reviewed_step_id="builder",
        focus_instructions=(
            "As Frontend Manager, review only the frontend/UI portions of the generated files and "
            "implementation plan. Judge interaction quality, usability, and whether the UI matches the "
            "approved scope. Ignore backend/API and database-schema concerns."
        ),
    )


def database_manager_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return invoke_management_review(
        agent_id="database_manager_agent",
        role_title="Database Manager Agent",
        role_description="Evaluates the generated data model and schema for soundness.",
        task=task,
        reviewed_step_id="builder",
        focus_instructions=(
            "As Database Manager, review only the data-model/schema/migration portions of the generated "
            "files and implementation plan. Judge whether the data model is sound, appropriately "
            "normalized, and matches the approved scope. Ignore backend business logic and frontend "
            "concerns."
        ),
    )


def quality_manager_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    return invoke_management_review(
        agent_id="quality_manager_agent",
        role_title="Quality Manager Agent",
        role_description="Evaluates review and test artifacts for release readiness.",
        task=task,
        reviewed_step_id="review",
        focus_instructions=(
            "As Quality Manager, judge whether the review findings and checklist indicate the build is "
            "ready to proceed to validation/testing and eventual release. Redirect if blocking issues "
            "remain unresolved; escalate if you cannot determine readiness from the available evidence."
        ),
    )
