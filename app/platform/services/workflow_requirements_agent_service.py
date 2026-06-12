from __future__ import annotations

import os
from typing import Any, Dict


AGENT_NAME = "platform_requirements_scoping_agent"


def build_requirements_scope(requirements: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _should_use_openai(payload):
        return _openai_scope(requirements)
    return _fallback_scope(requirements, "deterministic")


def build_code_blueprint(requirements: str, scope_markdown: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _should_use_openai(payload):
        return _openai_code(requirements, scope_markdown)
    return _fallback_code(requirements, "deterministic")


def _should_use_openai(payload: Dict[str, Any]) -> bool:
    mode = str(payload.get("agent_mode") or "").lower()
    return mode == "openai" and bool(os.getenv("OPENAI_API_KEY"))


def _openai_scope(requirements: str) -> Dict[str, Any]:
    prompt = (
        "You are the platform requirements scoping agent for an enterprise AI Software Factory. "
        "Convert the operator request into clear Markdown. Include: Summary, Clarifying Questions, "
        "Scope of Work, Acceptance Criteria, Risks, and Approval Gate. Do not write code yet.\n\n"
        f"Operator request:\n{requirements}"
    )
    try:
        from app.core.llm import get_llm

        response = get_llm().invoke(prompt)
        return {
            "agent_name": AGENT_NAME,
            "agent_status": "openai_completed",
            "scope_markdown": getattr(response, "content", str(response)),
        }
    except Exception as error:  # pragma: no cover - provider/network dependent
        fallback = _fallback_scope(requirements, "openai_failed")
        return {**fallback, "agent_error": str(error)}


def _openai_code(requirements: str, scope_markdown: str) -> Dict[str, Any]:
    prompt = (
        "You are the platform module code planning agent. Produce a concise copyable code blueprint "
        "and file plan only. Do not push to GitHub. Do not deploy. Keep Python 3.9 compatibility.\n\n"
        f"Requirements:\n{requirements}\n\nApproved scope:\n{scope_markdown}"
    )
    try:
        from app.core.llm import get_llm

        response = get_llm().invoke(prompt)
        return {
            "agent_name": "platform_code_blueprint_agent",
            "agent_status": "openai_completed",
            "generated_code": getattr(response, "content", str(response)),
        }
    except Exception as error:  # pragma: no cover - provider/network dependent
        fallback = _fallback_code(requirements, "openai_failed")
        return {**fallback, "agent_error": str(error)}


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
