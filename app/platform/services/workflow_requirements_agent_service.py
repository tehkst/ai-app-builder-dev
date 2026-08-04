from __future__ import annotations

from typing import Any, Dict


AGENT_NAME = "platform_requirements_scoping_agent"


def build_requirements_scope(requirements: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _should_use_ai(payload):
        return _ai_scope(requirements)
    return _fallback_scope(requirements, "deterministic")


def build_code_blueprint(requirements: str, scope_markdown: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _should_use_ai(payload):
        return _ai_code(requirements, scope_markdown)
    return _fallback_code(requirements, "deterministic")


def _should_use_ai(payload: Dict[str, Any]) -> bool:
    # "openai" is this feature's existing external request contract (agent_mode), kept
    # as-is - the real provider actually used is resolved from the Mission Control AI
    # provider setting below, not hardcoded to OpenAI.
    mode = str(payload.get("agent_mode") or "").lower()
    return mode == "openai"


def _ai_scope(requirements: str) -> Dict[str, Any]:
    from app.platform.runtime.service import invoke_ai

    system = (
        "You are the platform requirements scoping agent for an enterprise AI Software Factory. "
        "Convert the operator request into clear Markdown. Include: Summary, Clarifying Questions, "
        "Scope of Work, Acceptance Criteria, Risks, and Approval Gate. Do not write code yet."
    )
    ai_result = invoke_ai({"system": system, "prompt": requirements})
    if ai_result.get("status") != "completed":
        fallback = _fallback_scope(requirements, "ai_failed")
        return {**fallback, "agent_error": str(ai_result.get("status"))}
    return {
        "agent_name": AGENT_NAME,
        "agent_status": "ai_completed",
        "scope_markdown": str(ai_result.get("output_text") or ""),
    }


def _ai_code(requirements: str, scope_markdown: str) -> Dict[str, Any]:
    from app.platform.runtime.service import invoke_ai

    system = (
        "You are the platform module code planning agent. Produce a concise copyable code blueprint "
        "and file plan only. Do not push to GitHub. Do not deploy. Keep Python 3.9 compatibility."
    )
    prompt = f"Requirements:\n{requirements}\n\nApproved scope:\n{scope_markdown}"
    ai_result = invoke_ai({"system": system, "prompt": prompt})
    if ai_result.get("status") != "completed":
        fallback = _fallback_code(requirements, "ai_failed")
        return {**fallback, "agent_error": str(ai_result.get("status"))}
    return {
        "agent_name": "platform_code_blueprint_agent",
        "agent_status": "ai_completed",
        "generated_code": str(ai_result.get("output_text") or ""),
    }


def _fallback_scope(requirements: str, status: str) -> Dict[str, Any]:
    scope = "\n".join(
        [
            "# Scope of Work",
            "",
            "## Summary",
            requirements,
            "",
            "## Clarifying Questions",
            "- Which billing provider should be used first?",
            "- Which subscription tiers and renewal rules are required?",
            "- Which admin roles can view invoices and payment status?",
            "",
            "## Acceptance Criteria",
            "- Admin can review the scoped billing request before code generation.",
            "- No GitHub push or Railway deploy is automated.",
            "- Output is copyable for manual migration.",
            "",
            "## Approval Gate",
            "Confirm Scope & Code is required before generation.",
        ]
    )
    return {"agent_name": AGENT_NAME, "agent_status": status, "scope_markdown": scope}


def _fallback_code(requirements: str, status: str) -> Dict[str, Any]:
    code = "\n".join(
        [
            "# Copyable module blueprint",
            f"REQUIREMENTS = {requirements!r}",
            "FILES = ['services/billing_service.py', 'api/billing_routes.py', 'agents/billing_check.py']",
            "NEXT_STEP = 'Paste this blueprint into GitHub manually for Railway deployment.'",
        ]
    )
    return {"agent_name": "platform_code_blueprint_agent", "agent_status": status, "generated_code": code}
