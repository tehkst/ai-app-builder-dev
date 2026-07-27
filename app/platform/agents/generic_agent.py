from __future__ import annotations

from typing import Any, Dict

from app.platform.runtime.ai_provider import AIProviderError
from app.platform.runtime.provider_router import invoke_provider

SAFETY_BOUNDARY = (
    "You may only think, analyze, and respond with text. You cannot write files, merge code, "
    "deploy, or perform any governed action directly - those remain founder-approved actions "
    "elsewhere in the platform. If the task requires such an action, describe what should happen "
    "and let a human route it through the appropriate governed workflow."
)


def build_generic_agent_handler(agent_id: str, name: str, description: str):
    """Build a closure-bound handler for an admin-created agent.

    Every admin-created agent shares this same LLM-driven execution path; the closure
    captures the specific agent's identity/description so the resulting AgentDefinition.handler
    signature (task -> result) matches every other registered agent.
    """

    def handler(task: Dict[str, Any]) -> Dict[str, Any]:
        input_payload = dict(task.get("input_payload") or {})
        operational_skills = input_payload.get("operational_skills") or {}
        skill_content = operational_skills.get("content") if operational_skills.get("loaded") else None

        system_lines = [
            "You are %s, an AI specialist agent within the AI Software Factory organisation." % name,
            "Role description: %s" % description,
        ]
        if skill_content:
            system_lines.append("Operational skill document:\n%s" % skill_content)
        system_lines.append(SAFETY_BOUNDARY)

        prompt = str(input_payload.get("goal") or task.get("description") or task.get("title") or "").strip()
        if not prompt:
            return {"success": False, "agent_id": agent_id, "error": "No task details were provided."}

        try:
            result = invoke_provider(provider=None, prompt=prompt, system="\n\n".join(system_lines), model=None)
        except AIProviderError as exc:
            return {"success": False, "agent_id": agent_id, "error": str(exc)}

        if result.status != "completed":
            return {
                "success": False,
                "agent_id": agent_id,
                "error": result.output_text or ("AI provider returned status: %s" % result.status),
            }

        return {
            "success": True,
            "agent_id": agent_id,
            "message": result.output_text,
            "provider": result.provider,
            "model": result.model,
            "safe_mode": True,
            "writes_code": False,
        }

    return handler
