from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.runtime.service import invoke_ai

SYSTEM_PROMPT = (
    "You are a product scoping analyst for a SaaS app-builder platform. Given a "
    "customer's plain-language app request, draft a clear scope of work. Return "
    "JSON only, matching the required schema exactly. Make reasonable, explicit "
    "assumptions rather than asking clarifying questions — this scope will be shown "
    "to the customer for approval before anything is built, and they can request "
    "changes afterward."
)

REQUIRED_SCHEMA = {
    "goal_summary": "one paragraph describing what the app does",
    "target_users": ["who uses this app and their roles"],
    "core_views": ["the screens/pages required for a first working version"],
    "data_entities": ["the main records the app must store"],
    "auth_model": "who can sign in and what each role can do",
    "acceptance_criteria": ["concrete, checkable statements that prove the app works"],
    "out_of_scope": ["things this first version explicitly will not include"],
    "risks": ["risks or ambiguities in the request"],
    "assumptions": ["assumptions made to fill gaps in the request"],
}


def draft_customer_app_scope(app_request: str, *, provider: str = None, model: str = None) -> Dict[str, Any]:
    """Draft a SOW for a customer app-build request using a real LLM call.

    Falls back to a minimal, clearly-flagged degraded scope if the provider is
    unavailable, so the approval flow still works end to end without a live key.
    """

    cleaned_request = " ".join((app_request or "").strip().split())
    if not cleaned_request:
        return _blocked("app_request is required.")

    ai_result = invoke_ai(
        {
            "provider": provider,
            "model": model,
            "system": SYSTEM_PROMPT,
            "prompt": json.dumps(
                {
                    "task": "Draft a scope of work for this app request.",
                    "required_schema": REQUIRED_SCHEMA,
                    "customer_request": cleaned_request,
                },
                sort_keys=True,
            ),
        }
    )

    if ai_result.get("status") != "completed":
        return _degraded_scope(cleaned_request, reason=f"AI scoping was unavailable: {ai_result.get('status')}.")

    drafted, parse_error = _parse_model_output(str(ai_result.get("output_text") or ""))
    if parse_error:
        return _degraded_scope(cleaned_request, reason=parse_error)

    normalized = {
        "app_idea": cleaned_request,
        "goal_summary": str(drafted.get("goal_summary") or "").strip(),
        "target_users": _string_list(drafted.get("target_users")),
        "core_views": _string_list(drafted.get("core_views")),
        "data_entities": _string_list(drafted.get("data_entities")),
        "auth_model": str(drafted.get("auth_model") or "").strip(),
        "acceptance_criteria": _string_list(drafted.get("acceptance_criteria")),
        "out_of_scope": _string_list(drafted.get("out_of_scope")),
        "risks": _string_list(drafted.get("risks")),
        "assumptions": _string_list(drafted.get("assumptions")),
    }

    return {
        "success": True,
        "status": "scope_ready",
        "approval_required": True,
        "degraded": False,
        "normalized_request": normalized,
        "scope_of_work_markdown": _render_markdown(normalized),
        "generation": {"provider": ai_result.get("provider"), "model": ai_result.get("model")},
    }


def _degraded_scope(app_request: str, *, reason: str) -> Dict[str, Any]:
    normalized = {
        "app_idea": app_request,
        "goal_summary": app_request,
        "target_users": ["End users"],
        "core_views": ["Home"],
        "data_entities": [],
        "auth_model": "Signed-in users only (default).",
        "acceptance_criteria": ["The app matches the customer's request."],
        "out_of_scope": [],
        "risks": [f"Scope was drafted without AI assistance: {reason}"],
        "assumptions": ["No AI-drafted detail is available; scope is a minimal placeholder pending provider availability."],
    }
    return {
        "success": True,
        "status": "scope_ready",
        "approval_required": True,
        "degraded": True,
        "degraded_reason": reason,
        "normalized_request": normalized,
        "scope_of_work_markdown": _render_markdown(normalized),
        "generation": {"provider": None, "model": None},
    }


def _bullets(items: List[str], empty_label: str) -> List[str]:
    return [f"- {item}" for item in items] if items else [f"- {empty_label}"]


def _render_markdown(normalized: Dict[str, Any]) -> str:
    lines = [
        "# Scope of Work",
        f"**Request:** {normalized['app_idea']}",
        "",
        f"**Goal:** {normalized['goal_summary'] or normalized['app_idea']}",
        "",
        "## Target Users",
        *_bullets(normalized["target_users"], "Not specified"),
        "",
        "## Core Views",
        *_bullets(normalized["core_views"], "Not specified"),
        "",
        "## Data Entities",
        *_bullets(normalized["data_entities"], "Not specified"),
        "",
        f"## Access Model\n{normalized['auth_model'] or 'Not specified'}",
        "",
        "## Acceptance Criteria",
        *_bullets(normalized["acceptance_criteria"], "Not specified"),
        "",
        "## Out of Scope",
        *_bullets(normalized["out_of_scope"], "Nothing explicitly excluded"),
        "",
        "## Risks",
        *_bullets(normalized["risks"], "None identified"),
        "",
        "## Assumptions",
        *_bullets(normalized["assumptions"], "None"),
    ]
    return "\n".join(lines)


def _parse_model_output(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError):
        return {}, "Scope draft was not valid structured JSON."
    if not isinstance(value, dict):
        return {}, "Scope draft must be a JSON object."
    return value, None


def _string_list(value: Any) -> List[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _blocked(reason: str) -> Dict[str, Any]:
    return {"success": False, "status": "invalid_request", "message": reason}


def draft_and_approve_customer_app_scope(
    db: Session,
    *,
    app_request: str,
    requested_by: str = "platform_admin",
) -> Dict[str, Any]:
    """Convenience helper: draft a SOW and immediately approve it.

    Used by callers (CLI/smoke checks) that want an approved scoping request in
    one step. The user-facing flow should draft and approve as two separate,
    explicit actions via /product-scope/draft and /product-scope/{id}/approve.
    """

    from app.platform.services.scoping_persistence_service import (
        approve_scoping_record,
        persist_scoping_analysis,
    )

    result = draft_customer_app_scope(app_request)
    if not result.get("success"):
        return result
    record = persist_scoping_analysis(
        db,
        result=result,
        llm_result={"status": "not_applicable"},
        requested_by=requested_by,
        request_kind="customer_app",
    )
    approved = approve_scoping_record(db, scoping_request_id=record["scoping_request_id"], approved_by=requested_by)
    return {**result, **(approved or record), "success": True}
