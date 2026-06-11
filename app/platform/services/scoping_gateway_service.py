from __future__ import annotations

from typing import Any, Dict, List


QUESTION_BANK = {
    "app_idea": {
        "label": "Request",
        "prompt": "Describe the app or platform change in one clear paragraph.",
    },
    "target_users": {
        "label": "Target users",
        "prompt": "Who will use this, and which roles need separate views?",
    },
    "core_views": {
        "label": "Core views",
        "prompt": "List the screens or admin surfaces required for the first release.",
    },
    "data_entities": {
        "label": "Data entities",
        "prompt": "List the main records the system must store or manage.",
    },
    "auth_model": {
        "label": "Access model",
        "prompt": "Explain who can sign in and what each role is allowed to do.",
    },
    "success_criteria": {
        "label": "Success criteria",
        "prompt": "Define the acceptance checks that prove this work is complete.",
    },
}

SELECT_FIELDS = {
    "mode_selector": "Mode Selector",
    "target_boundary": "Target Parameters",
    "change_classification": "Change Classification",
}


def analyze_scoping_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_payload(payload)
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
    scope = payload.get("scope_of_work_markdown") or ""
    request = _normalize_payload(payload.get("normalized_request") or payload)
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
        "generation_started": False,
        "safety_flags": _safety_flags(),
    }


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
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
        "executes_generated_code": False,
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
