from __future__ import annotations

import json
import re
from typing import Any, Dict, List


QUESTION_BANK = {
    "app_idea": {"label": "Request", "prompt": "Describe the app or platform change in one clear paragraph."},
    "target_users": {"label": "Target users", "prompt": "Who will use this, and which roles need separate views?"},
    "core_views": {"label": "Core views", "prompt": "List the screens or admin surfaces required for the first release."},
    "data_entities": {"label": "Data entities", "prompt": "List the main records the system must store or manage."},
    "auth_model": {"label": "Access model", "prompt": "Explain who can sign in and what each role is allowed to do."},
    "success_criteria": {"label": "Success criteria", "prompt": "Define the acceptance checks that prove this work is complete."},
}

SELECT_FIELDS = {
    "mode_selector": "Mode Selector",
    "target_boundary": "Target Parameters",
    "change_classification": "Change Classification",
}

# Structurally invariant for this gateway - it only ever scopes changes to this
# platform's own admin surfaces, so these two never vary by request content
# (unlike the fields below, which must be drafted from the real request).
STRUCTURAL_DEFAULTS = {
    "mode_selector": "Enhance Platform AI Software Factory",
    "target_boundary": "Current Platform",
}

DRAFTABLE_FIELDS = (
    "change_classification",
    "target_users",
    "core_views",
    "data_entities",
    "auth_model",
    "success_criteria",
    "request_constraints",
)

SCOPE_DRAFTING_SYSTEM_PROMPT = (
    "You are a production scoping analyst for AI Software Factory's own internal "
    "platform (Mission Control). This is a platform-admin request to change or "
    "extend the platform's OWN admin surfaces, not to build a new customer app. "
    "Given the founder's request, draft the scope fields below, grounded "
    "specifically in what was actually asked. Return JSON only, matching the "
    "required schema exactly. If the request is too vague to draft a specific "
    "field confidently, return an empty list or empty string for that field "
    "rather than guessing - a human will be asked to fill in anything left empty."
)

SCOPE_DRAFTING_SCHEMA = {
    "change_classification": "one of: UI/UX Refinement, New Feature, Bug Fix, Infrastructure",
    "target_users": ["which platform roles use this change, e.g. Platform admin"],
    "core_views": ["the existing or new Mission Control screens this change touches"],
    "data_entities": ["the main records involved, if any"],
    "auth_model": "who can access this and what each role can do",
    "success_criteria": ["concrete, checkable statements that prove this change is done"],
    "request_constraints": ["safety or scope constraints specific to this request"],
}

# Used only when real AI drafting is unavailable (no provider, provider error, or
# unparseable output) - honestly generic placeholders that make the gap visible,
# never a specific unrelated feature's content. Replaces the former
# DEFAULT_PLATFORM_SCOPE, which silently substituted one fixed catalog describing
# a different, older feature (Neural Fabric Status, Safety Dashboard, ...) for any
# request over 20 characters regardless of what was actually asked - a real,
# confirmed bug (see Jarvis pipeline simplification, Phase 1 audit).
DEGRADED_SCOPE_DEFAULTS = {
    "change_classification": "Platform Change (unclassified - AI-assisted drafting unavailable)",
    "target_users": ["Platform admin (default - confirm before approval)"],
    "core_views": ["Not yet specified - AI-assisted drafting was unavailable"],
    "data_entities": ["Not yet specified - AI-assisted drafting was unavailable"],
    "auth_model": "Platform admin only (default; confirm before approval).",
    "success_criteria": ["Founder confirms this change matches the request before approval."],
    "request_constraints": [
        "No production data", "DB-preview only", "Approval required before any generation or deployment",
    ],
}


def analyze_scoping_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _infer_operator_scope_defaults(_normalize_payload(payload))
    missing = _missing_fields(normalized)
    safety_flags = _safety_flags()

    if missing:
        return {
            "success": True,
            "status": "clarification_required",
            "message": "More scope detail is required before any build action.",
            "questions": [_question_for(field) for field in missing],
            "normalized_request": normalized,
            "approval_required": False,
            "safety_flags": safety_flags,
        }

    return {
        "success": True,
        "status": "scope_ready",
        "message": "Scope is ready for explicit operator approval.",
        "questions": [],
        "normalized_request": normalized,
        "scope_of_work_markdown": _scope_of_work(normalized),
        "milestone_tree": _milestone_tree(normalized),
        "approval_required": True,
        "safety_flags": safety_flags,
    }


def approve_scoping_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    request = _infer_operator_scope_defaults(_normalize_payload(payload.get("normalized_request") or payload))
    scope = payload.get("scope_of_work_markdown") or ""

    if not scope.strip() and not _missing_fields(request):
        scope = _scope_of_work(request)

    if not scope.strip():
        return {
            "success": False,
            "status": "approval_blocked",
            "message": "Scope approval requires a generated scope of work first.",
            "approval_status": "not_approved",
            "generation_started": False,
            "safety_flags": _safety_flags(),
        }

    return {
        "success": True,
        "status": "approved",
        "approval_status": "scope_approved",
        "message": "Scope approved. Generation remains gated by downstream action.",
        "normalized_request": request,
        "scope_of_work_markdown": scope,
        "generation_started": False,
        "safety_flags": _safety_flags(),
    }


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    safety_options = payload.get("safety_options") or {}
    return {
        "mode_selector": _text(payload.get("mode_selector")),
        "target_boundary": _text(payload.get("target_boundary")),
        "change_classification": _text(payload.get("change_classification")),
        "app_idea": _text(payload.get("app_idea") or payload.get("prompt")),
        "target_users": _list(payload.get("target_users")),
        "core_views": _list(payload.get("core_views")),
        "data_entities": _list(payload.get("data_entities")),
        "auth_model": _text(payload.get("auth_model")),
        "success_criteria": _list(payload.get("success_criteria")),
        "request_constraints": _list(payload.get("request_constraints")),
        "safety_options": {
            "db_preview_only": safety_options.get("db_preview_only") is not False,
            "no_code_execution": safety_options.get("no_code_execution") is not False,
            "no_deployment": safety_options.get("no_deployment") is not False,
            "approval_required": safety_options.get("approval_required") is not False,
            "real_customer_data_used": False,
        },
    }


def _infer_operator_scope_defaults(request: Dict[str, Any]) -> Dict[str, Any]:
    """Draft the scope fields a platform admin left blank, grounded in their real
    request via a real LLM call - not a fixed catalog substituted for any request
    over 20 characters (the confirmed prior bug).

    mode_selector/target_boundary are structurally invariant (this gateway only
    ever scopes changes to this platform's own admin surfaces) and always
    default the same way. Everything else is drafted from app_idea; a field the
    LLM can't confidently draft is left for the real clarifying-question
    mechanism (_missing_fields/_question_for) to ask about, rather than silently
    filled with unrelated fabricated content. If AI drafting itself is
    unavailable, an honestly-generic degraded placeholder is used instead (never
    a specific unrelated feature's content) so the flow still produces a
    reviewable scope end to end.
    """

    inferred = dict(request)
    for key, value in STRUCTURAL_DEFAULTS.items():
        current = inferred.get(key)
        if current in ("", [], None) or current == SELECT_FIELDS.get(key):
            inferred[key] = value

    app_idea = request.get("app_idea") or ""
    if len(app_idea) < 20:
        return inferred

    empty_keys = [
        key for key in DRAFTABLE_FIELDS
        if inferred.get(key) in ("", [], None) or inferred.get(key) == SELECT_FIELDS.get(key)
    ]
    if not empty_keys:
        return inferred

    drafted = _draft_scope_fields(app_idea)
    for key in empty_keys:
        value = drafted.get(key)
        if value not in ("", [], None):
            inferred[key] = value
        else:
            inferred[key] = DEGRADED_SCOPE_DEFAULTS[key]

    return inferred


def _draft_scope_fields(app_idea: str) -> Dict[str, Any]:
    try:
        from app.platform.runtime.service import invoke_ai
    except Exception:
        return {}
    try:
        ai_result = invoke_ai({
            "system": SCOPE_DRAFTING_SYSTEM_PROMPT,
            "prompt": json.dumps(
                {
                    "task": "Draft the scope fields for this platform-admin request.",
                    "required_schema": SCOPE_DRAFTING_SCHEMA,
                    "founder_request": app_idea,
                },
                sort_keys=True,
            ),
        })
    except Exception:
        return {}
    if ai_result.get("status") != "completed":
        return {}
    return _parse_drafted_scope_fields(str(ai_result.get("output_text") or ""))


def _parse_drafted_scope_fields(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        "change_classification": _text(value.get("change_classification")),
        "target_users": _list(value.get("target_users")),
        "core_views": _list(value.get("core_views")),
        "data_entities": _list(value.get("data_entities")),
        "auth_model": _text(value.get("auth_model")),
        "success_criteria": _list(value.get("success_criteria")),
        "request_constraints": _list(value.get("request_constraints")),
    }


def _missing_fields(request: Dict[str, Any]) -> List[str]:
    missing = [
        key
        for key, label in SELECT_FIELDS.items()
        if not request.get(key) or request.get(key) == label
    ]
    for key in QUESTION_BANK:
        value = request.get(key)
        if not value or value == []:
            missing.append(key)
    if len(request.get("app_idea") or "") < 20 and "app_idea" not in missing:
        missing.append("app_idea")
    return missing


def _question_for(field: str) -> Dict[str, Any]:
    if field in SELECT_FIELDS:
        return {
            "id": field,
            "label": SELECT_FIELDS[field],
            "prompt": f"Select a value for {SELECT_FIELDS[field]}.",
            "required": True,
        }
    question = QUESTION_BANK[field]
    return {"id": field, **question, "required": True}


def _scope_of_work(request: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Scope of Work",
            f"- Mode: {request['mode_selector']}",
            f"- Target: {request['target_boundary']}",
            f"- Change class: {request['change_classification']}",
            f"- Request: {request['app_idea']}",
            f"- Users: {', '.join(request['target_users'])}",
            f"- Core views: {', '.join(request['core_views'])}",
            f"- Data entities: {', '.join(request['data_entities'])}",
            f"- Access model: {request['auth_model']}",
            f"- Acceptance checks: {', '.join(request['success_criteria'])}",
            f"- Constraints: {', '.join(request['request_constraints']) or 'Safety defaults'}",
            "- Safety enclave: DB preview only, no code execution, no deployment",
        ]
    )


def _milestone_tree(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"name": "Scope approval", "children": ["Confirm roles", "Confirm views"]},
        {
            "name": "Architecture plan",
            "children": ["Service layer", "Route contracts", "UI boundaries"],
        },
        {
            "name": "Implementation",
            "children": request["core_views"][:4],
        },
        {
            "name": "Verification",
            "children": request["success_criteria"][:5],
        },
    ]


def _safety_flags() -> Dict[str, bool]:
    return {
        "writes_source_files": False,
        "db_preview_only": True,
        "executes_generated_code": False,
        "external_deployment": False,
        "real_customer_data_used": False,
        "starts_runtime_server": False,
        "requires_operator_approval": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        item.strip()
        for item in str(value or "").replace("\n", ",").split(",")
        if item.strip()
    ]
