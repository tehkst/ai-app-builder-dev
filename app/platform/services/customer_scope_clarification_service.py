from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.platform.organization_console.skills import read_skill_document
from app.platform.runtime.ai_provider import AIProviderError
from app.platform.runtime.provider_router import invoke_provider

MAX_CLARIFICATION_ROUNDS = 2

_DECISION_INSTRUCTIONS = (
    "You must respond with a single JSON object only, no prose outside it, matching exactly this "
    'shape: {"needs_clarification": true|false, "question": "<one specific clarifying question, or '
    'null>", "reasoning": "<why>"}. Only ask a question when the request is genuinely ambiguous in a '
    "way that would materially change what gets built - never ask about implementation details a "
    "builder can reasonably infer or decide on its own. If the request is already clear enough to "
    "scope into a Statement of Work, set needs_clarification to false."
)


def assess_customer_app_clarity(
    app_request: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    *,
    round_number: int = 0,
) -> Dict[str, Any]:
    """One real CEO-agent judgment call: is this customer's app request clear enough to draft
    a Statement of Work, or does it need one clarifying question first?

    Reuses the CEO agent's real identity/skill document (the same
    organization_console.skills.read_skill_document("ceo_agent") every management-tier handler
    reads), not invoke_management_review itself - that function's decision contract is exactly
    approve/redirect/escalate with no fourth "ask a question" state, and three other real
    callers already depend on that exact shape, so overloading it here would be the wrong reuse.

    Bounded server-side, not model-trusted: once round_number reaches MAX_CLARIFICATION_ROUNDS,
    this always returns needs_clarification=False regardless of what the model says, so a
    founder who has already answered enough questions can always proceed to a SOW rather than
    facing an unbounded interrogation.
    """
    history = conversation_history or []
    if round_number >= MAX_CLARIFICATION_ROUNDS:
        return {
            "needs_clarification": False,
            "question": None,
            "reasoning": "Reached the maximum number of clarifying rounds; proceeding with what has been provided.",
            "bounded": True,
        }

    skill_document = read_skill_document("ceo_agent")
    skill_content = skill_document.get("content") if (skill_document.get("validation") or {}).get("valid") else None

    system_lines = [
        "You are the CEO Agent within the AI Software Factory organisation, speaking directly with "
        "a customer who wants to build an app on this platform.",
        "Role: understand what the customer actually wants before it gets scoped into a formal "
        "Statement of Work, by asking one real clarifying question when - and only when - the "
        "request is genuinely ambiguous in a way that would materially change what gets built.",
    ]
    if skill_content:
        system_lines.append("Operational skill document:\n%s" % skill_content)
    system_lines.append(_DECISION_INSTRUCTIONS)

    prompt_lines = ["Customer's app request: %s" % app_request]
    if history:
        prompt_lines.append("Clarification so far:")
        for turn in history:
            prompt_lines.append("Q: %s\nA: %s" % (turn.get("question", ""), turn.get("answer", "")))

    try:
        result = invoke_provider(
            provider=None, prompt="\n\n".join(prompt_lines), system="\n\n".join(system_lines), model=None,
        )
    except AIProviderError as exc:
        return {
            "needs_clarification": False, "question": None,
            "reasoning": "AI provider unavailable (%s); proceeding without a clarifying question." % exc,
            "degraded": True,
        }

    if result.status != "completed":
        return {
            "needs_clarification": False, "question": None,
            "reasoning": "AI provider call did not complete; proceeding without a clarifying question.",
            "degraded": True,
        }

    parsed = _parse_clarity(result.output_text)
    return {**parsed, "provider": result.provider, "model": result.model}


def _parse_clarity(output_text: Optional[str]) -> Dict[str, Any]:
    text = (output_text or "").strip()
    candidate = text
    if "```" in candidate:
        parts = candidate.split("```")
        if len(parts) >= 2:
            candidate = parts[1]
            if candidate.lstrip().lower().startswith("json"):
                candidate = candidate.lstrip()[4:]
    candidate = candidate.strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start:end + 1]

    try:
        parsed = json.loads(candidate)
    except (TypeError, ValueError):
        return {
            "needs_clarification": False, "question": None,
            "reasoning": "Could not parse a structured clarity assessment; proceeding.",
            "parse_error": True,
        }

    question = str(parsed.get("question") or "").strip() or None
    needs_clarification = bool(parsed.get("needs_clarification")) and question is not None
    return {
        "needs_clarification": needs_clarification,
        "question": question,
        "reasoning": str(parsed.get("reasoning") or "").strip(),
    }
