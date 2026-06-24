"""Smoke check for one-prompt platform operator scoping.

The production operator should not need to manually fill target users, core views,
data entities, access model, success criteria, and constraints before the platform
can create an approval-ready scope.
"""

from __future__ import annotations

import json

from app.platform.services.scoping_gateway_service import analyze_scoping_request, approve_scoping_request


ONE_PROMPT_REQUEST = """
Build a Platform UI Agent for AI Software Factory.

The current platform admin UI is too confusing for operator use. Create a clean,
guided production operator experience that lets the platform owner start self-build
and self-healing work without understanding internal milestone panels.
""".strip()


def run_operator_one_prompt_scoping_check() -> dict:
    analysis = analyze_scoping_request(
        {
            "app_idea": ONE_PROMPT_REQUEST,
            "mode_selector": "Enhance Platform AI Software Factory",
            "target_boundary": "Current Platform",
            "change_classification": "UI/UX Refinement",
            "safety_options": {
                "db_preview_only": True,
                "no_code_execution": True,
                "no_deployment": True,
                "approval_required": True,
            },
        }
    )

    approval = approve_scoping_request(
        {
            "normalized_request": analysis.get("normalized_request"),
            "scope_of_work_markdown": analysis.get("scope_of_work_markdown"),
        }
    )

    normalized = analysis.get("normalized_request") or {}
    inferred_fields_present = all(
        normalized.get(key)
        for key in (
            "target_users",
            "core_views",
            "data_entities",
            "auth_model",
            "success_criteria",
            "request_constraints",
        )
    )

    success = (
        analysis.get("status") == "scope_ready"
        and analysis.get("questions") == []
        and bool(analysis.get("scope_of_work_markdown"))
        and approval.get("success") is True
        and approval.get("approval_status") == "scope_approved"
        and inferred_fields_present
        and analysis.get("safety_flags", {}).get("db_preview_only") is True
        and analysis.get("safety_flags", {}).get("executes_generated_code") is False
        and analysis.get("safety_flags", {}).get("external_deployment") is False
    )

    return {
        "success": success,
        "one_prompt_operator_scope_ready": analysis.get("status") == "scope_ready",
        "clarification_count": len(analysis.get("questions") or []),
        "inferred_fields_present": inferred_fields_present,
        "approval_status": approval.get("approval_status"),
        "generation_started": approval.get("generation_started"),
        "safety_flags": analysis.get("safety_flags"),
        "normalized_request": normalized,
    }


def main() -> None:
    result = run_operator_one_prompt_scoping_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
