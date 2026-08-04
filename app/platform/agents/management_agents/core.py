from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.platform.agents.generic_agent import SAFETY_BOUNDARY
from app.platform.agents.workflow_step_context import _dependency_output_for_step, _goal
from app.platform.organization_console.skills import read_skill_document
from app.platform.runtime.ai_provider import AIProviderError
from app.platform.runtime.provider_router import invoke_provider

_VALID_DECISIONS = {"approve", "redirect", "escalate"}

_DECISION_INSTRUCTIONS = (
    "You must respond with a single JSON object only, no prose outside it, matching exactly this shape: "
    '{"decision": "approve" | "redirect" | "escalate", "rationale": "<why>", '
    '"concerns": ["<specific concern>", ...], "redirect_instructions": "<what should change, or null>"}. '
    '"approve" means the work may proceed as-is. "redirect" means it needs specific, describable changes '
    "before proceeding - the team can act on redirect_instructions without another human. \"escalate\" means "
    "this decision is beyond what you should resolve alone and needs founder/human judgment - use this "
    "when you are genuinely uncertain, not as a default."
)


def _parse_decision(output_text: Optional[str]) -> Dict[str, Any]:
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
    except (json.JSONDecodeError, ValueError):
        return {
            "decision": "escalate",
            "rationale": (
                "Could not parse a structured decision from the model response; conservatively "
                "escalating. Raw response: %s" % text[:1000]
            ),
            "concerns": [],
            "redirect_instructions": None,
            "parse_error": True,
        }

    decision = str(parsed.get("decision") or "").strip().lower()
    if decision not in _VALID_DECISIONS:
        return {
            "decision": "escalate",
            "rationale": (
                "Model returned an unrecognized decision value (%r); conservatively escalating. %s"
                % (decision, str(parsed.get("rationale") or ""))
            ),
            "concerns": parsed.get("concerns") if isinstance(parsed.get("concerns"), list) else [],
            "redirect_instructions": parsed.get("redirect_instructions"),
            "parse_error": True,
        }

    return {
        "decision": decision,
        "rationale": str(parsed.get("rationale") or "").strip() or "No rationale provided.",
        "concerns": parsed.get("concerns") if isinstance(parsed.get("concerns"), list) else [],
        "redirect_instructions": parsed.get("redirect_instructions") if decision == "redirect" else None,
        "parse_error": False,
    }


def _escalation_result(*, agent_id: str, role_title: str, message: str, rationale: str,
                        reviewed_step_id: Optional[str], reviewed_artifact_available: bool) -> Dict[str, Any]:
    return {
        "success": False,
        "agent_id": agent_id,
        "message": message,
        "decision": "escalate",
        "rationale": rationale,
        "concerns": [],
        "redirect_instructions": None,
        "reviewed_step_id": reviewed_step_id,
        "reviewed_artifact_available": reviewed_artifact_available,
        "safe_mode": True,
        "writes_code": False,
    }


def invoke_management_review(
    *,
    agent_id: str,
    role_title: str,
    role_description: str,
    task: Dict[str, Any],
    reviewed_step_id: Optional[str],
    focus_instructions: str,
) -> Dict[str, Any]:
    """Shared core for every management-tier handler: loads the agent's own skill
    doc, pulls the real upstream artifact it's meant to review (if any), calls a
    real LLM, and returns a structured approve/redirect/escalate decision - never
    a free-text blob. Any failure mode (provider error, incomplete response,
    unparseable output) conservatively escalates rather than defaulting to
    approve, since `success` here directly drives whether the workflow executor
    blocks downstream steps.
    """
    goal = _goal(task)
    skill_document = read_skill_document(agent_id)
    skill_valid = bool((skill_document.get("validation") or {}).get("valid"))
    skill_content = skill_document.get("content") if skill_valid else None

    reviewed_artifact = _dependency_output_for_step(task, reviewed_step_id) if reviewed_step_id else {}
    reviewed_artifact_available = bool(reviewed_artifact)
    prior_redirect_instructions = str(task.get("prior_redirect_instructions") or "").strip()

    system_lines: List[str] = [
        "You are the %s within the AI Software Factory organisation." % role_title,
        "Role: %s" % role_description,
    ]
    if skill_content:
        system_lines.append("Operational skill document:\n%s" % skill_content)
    system_lines.append(SAFETY_BOUNDARY)
    system_lines.append(_DECISION_INSTRUCTIONS)

    prompt_lines = ["Goal for this build: %s" % goal, focus_instructions]
    if reviewed_artifact_available:
        # A real architecture_plan (technology stack, full DB schema, API contracts,
        # file structure) routinely runs 8-9k+ characters once architect_agent drafts
        # a genuinely concrete plan - the old 6000-char cutoff sliced mid-object,
        # producing invalid-looking JSON the reviewer correctly could not parse and
        # reported as "truncated and unavailable for review" (a real, reproduced bug).
        # Raised again: a real regenerated plan (after a redirect actually gets acted
        # on - see agent_workflow_executor_service's _run_step_via_bridge) measured
        # 28018 characters here, above the previous 20000-char cutoff - regeneration
        # makes plans genuinely larger, not smaller. Any real truncation is still
        # stated explicitly rather than left for the reviewer to guess at.
        serialized_artifact = json.dumps(reviewed_artifact, indent=2, default=str)
        artifact_char_limit = 40000
        artifact_text = serialized_artifact[:artifact_char_limit]
        if len(serialized_artifact) > artifact_char_limit:
            artifact_text += (
                "\n... [truncated - the artifact exceeds the display limit; judge based on what "
                "is shown here rather than treating this as an incomplete or invalid artifact]"
            )
        prompt_lines.append("Artifact under review (from step %r):\n%s" % (reviewed_step_id, artifact_text))
    elif reviewed_step_id:
        prompt_lines.append(
            "No upstream artifact was available to review for step %r - evaluate based on the goal alone."
            % reviewed_step_id
        )
    if prior_redirect_instructions:
        # One bounded automatic retry after a "redirect" decision - the team is expected
        # to have acted on redirect_instructions without another human in the loop, so
        # this attempt must confirm whether that actually happened, not re-ask the same
        # question from scratch. If the same or a new concern remains, escalate rather
        # than redirect again - this is the only retry this step gets.
        prompt_lines.append(
            "A previous review of this same work already redirected with these instructions: %r. "
            "Confirm whether they were actually addressed. If they were, approve. If they were not "
            "addressed, or a new concern is present, escalate rather than redirecting again - this "
            "step has already used its one automatic redirect." % prior_redirect_instructions
        )

    try:
        result = invoke_provider(provider=None, prompt="\n\n".join(prompt_lines), system="\n\n".join(system_lines), model=None)
    except AIProviderError as exc:
        return _escalation_result(
            agent_id=agent_id, role_title=role_title,
            message="%s could not reach an AI provider; conservatively escalating." % role_title,
            rationale=str(exc), reviewed_step_id=reviewed_step_id,
            reviewed_artifact_available=reviewed_artifact_available,
        )

    if result.status != "completed":
        return _escalation_result(
            agent_id=agent_id, role_title=role_title,
            message="%s's AI provider call did not complete; conservatively escalating." % role_title,
            rationale=result.output_text or ("AI provider returned status: %s" % result.status),
            reviewed_step_id=reviewed_step_id, reviewed_artifact_available=reviewed_artifact_available,
        )

    parsed = _parse_decision(result.output_text)
    decision = parsed["decision"]
    return {
        "success": decision == "approve",
        "agent_id": agent_id,
        "message": "%s decision: %s." % (role_title, decision),
        "decision": decision,
        "rationale": parsed["rationale"],
        "concerns": parsed["concerns"],
        "redirect_instructions": parsed["redirect_instructions"],
        "reviewed_step_id": reviewed_step_id,
        "reviewed_artifact_available": reviewed_artifact_available,
        "provider": result.provider,
        "model": result.model,
        "safe_mode": True,
        "writes_code": False,
    }
