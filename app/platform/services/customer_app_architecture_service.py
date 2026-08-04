from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from app.platform.runtime.service import invoke_ai

SYSTEM_PROMPT = (
    "You are a software architect for an AI Software Factory customer app-build pipeline. "
    "Given the approved scope of work for a customer's app request, draft a concrete, "
    "buildable technical architecture plan - specific enough that a builder can act on it "
    "without guessing or inventing missing decisions. Return JSON only, matching the "
    "required schema exactly. Be concrete: name real technologies, real table/column "
    "names, real endpoint paths - never generic placeholders like 'TBD' or 'standard REST API'."
)

REQUIRED_SCHEMA = {
    "technology_stack": {
        "backend": "e.g. FastAPI + SQLAlchemy",
        "frontend": "e.g. React + TypeScript",
        "database": "e.g. PostgreSQL",
        "other": ["other real technology choices, e.g. Redis for session cache"],
    },
    "database_schema": [
        {"table": "table name", "columns": ["column_name: type - purpose", "..."]},
    ],
    "api_contracts": [
        {
            "method": "GET|POST|PUT|DELETE",
            "path": "/api/...",
            "purpose": "what this endpoint does",
            "request_body": {"field_name": "type - purpose, or null if this method has no body"},
            "response_body": {"field_name": "type - purpose"},
        },
    ],
    "component_tree": ["top-level UI pages/components and their real nesting for this specific app"],
    "file_structure": [
        "real, request-specific top-level file/module paths, not a generic template - include a "
        "frontend API client/types file (e.g. frontend/src/types/index.ts or api-client.ts) that "
        "defines the TypeScript types/DTOs matching the request_body/response_body shapes above",
    ],
    "concurrency_handling": "how simultaneous conflicting operations specific to this app are prevented",
    "architecture_summary": "one paragraph overview of the technical approach",
    "architecture_constraints": ["real constraints or risks this architecture must respect"],
}


def draft_customer_app_architecture(
    *,
    app_request: str,
    scope_of_work_markdown: str = "",
    acceptance_criteria: List[str] = None,
    out_of_scope: List[str] = None,
    provider: str = None,
    model: str = None,
) -> Dict[str, Any]:
    """Draft a real, request-specific technical architecture using a real LLM call.

    Replaces architect_agent_handler's former hardcoded placeholder ("Legacy
    application workflow preview; not authoritative...", empty integration_contracts,
    no technology stack/schema/contracts at all) that every customer SaaS build hit,
    since that pipeline has no Mission Control MISSION-* identity - see this
    function's caller. Falls back to a minimal, honestly-flagged degraded plan if
    the provider is unavailable, matching customer_app_scope_service.
    draft_customer_app_scope's established discipline, so the pipeline still
    produces something reviewable end to end without a live key.
    """

    cleaned_request = " ".join((app_request or "").strip().split())
    if not cleaned_request:
        return _degraded_plan(reason="app_request is required.")

    ai_result = invoke_ai(
        {
            "provider": provider,
            "model": model,
            "system": SYSTEM_PROMPT,
            "prompt": json.dumps(
                {
                    "task": "Draft a concrete technical architecture plan for this approved app request.",
                    "required_schema": REQUIRED_SCHEMA,
                    "app_request": cleaned_request,
                    "scope_of_work_markdown": scope_of_work_markdown,
                    "acceptance_criteria": acceptance_criteria or [],
                    "out_of_scope": out_of_scope or [],
                },
                sort_keys=True,
            ),
        }
    )

    if ai_result.get("status") != "completed":
        return _degraded_plan(reason=f"AI architecture drafting was unavailable: {ai_result.get('status')}.")

    drafted, parse_error = _parse_model_output(str(ai_result.get("output_text") or ""))
    if parse_error:
        return _degraded_plan(reason=parse_error)

    plan = {
        "technology_stack": drafted.get("technology_stack") if isinstance(drafted.get("technology_stack"), dict) else {},
        "database_schema": drafted.get("database_schema") if isinstance(drafted.get("database_schema"), list) else [],
        "api_contracts": drafted.get("api_contracts") if isinstance(drafted.get("api_contracts"), list) else [],
        "component_tree": _string_list(drafted.get("component_tree")),
        "file_structure": _string_list(drafted.get("file_structure")),
        "concurrency_handling": str(drafted.get("concurrency_handling") or "").strip(),
        "architecture_summary": str(drafted.get("architecture_summary") or "").strip(),
        "architecture_constraints": _string_list(drafted.get("architecture_constraints")),
    }

    return {
        "success": True,
        "degraded": False,
        "architecture_plan": plan,
        "generation": {"provider": ai_result.get("provider"), "model": ai_result.get("model")},
    }


def _degraded_plan(*, reason: str) -> Dict[str, Any]:
    return {
        "success": True,
        "degraded": True,
        "degraded_reason": reason,
        "architecture_plan": {
            "technology_stack": {},
            "database_schema": [],
            "api_contracts": [],
            "component_tree": [],
            "file_structure": [],
            "concurrency_handling": "",
            "architecture_summary": f"AI-assisted architecture drafting was unavailable: {reason}",
            "architecture_constraints": [
                "Architecture drafting was unavailable - do not proceed to implementation until a real plan is drafted.",
            ],
        },
        "generation": {"provider": None, "model": None},
    }


def _parse_model_output(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError):
        return {}, "Architecture draft was not valid structured JSON."
    if not isinstance(value, dict):
        return {}, "Architecture draft must be a JSON object."
    return value, None


def _string_list(value: Any) -> List[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []
