from __future__ import annotations

from typing import Any, Callable

from app.platform.board_room.executive_intelligence_orchestrator import (
    ExecutiveIntelligenceOrchestrator,
)
from app.platform.board_room.executive_response_critic import ExecutiveResponseCritic
from app.platform.board_room.jarvis_prompt_builder import JarvisPromptBuilder


class JarvisCognitiveCore:
    """Plans and critiques founder conversation; it has no execution authority."""

    @classmethod
    def respond(
        cls,
        *,
        founder_message: str,
        mode: str,
        context: dict[str, Any],
        invoke: Callable[[dict[str, Any]], dict[str, Any]],
        decomposition: dict[str, Any] | None = None,
        provider: Any = None,
        model: Any = None,
    ) -> str:
        plan = ExecutiveIntelligenceOrchestrator().plan(
            founder_message,
            mode=mode,
            context=context,
            decomposition=decomposition,
        )
        payload = {
            "system": JarvisPromptBuilder.system_prompt(mode, plan.perspective),
            "prompt": JarvisPromptBuilder.user_prompt(
                founder_message, context, mode, plan.executive_brief
            ),
            "provider": provider,
            "model": model,
        }
        result = invoke(payload)
        draft = str(result.get("output_text") or "").strip()
        quality = ExecutiveResponseCritic.evaluate(
            draft,
            mode=mode,
            founder_message=founder_message,
            executive_brief=plan.executive_brief,
        )
        if quality.acceptable:
            return draft
        if draft and plan.uses_decision_engine:
            revision = invoke({
                **payload,
                "prompt": payload["prompt"]
                + "\n\nDraft to revise:\n"
                + draft
                + "\n\nBounded revision instruction:\n"
                + quality.revision_instruction,
            })
            revised = str(revision.get("output_text") or "").strip()
            revised_quality = ExecutiveResponseCritic.evaluate(
                revised,
                mode=mode,
                founder_message=founder_message,
                executive_brief=plan.executive_brief,
            )
            if revised_quality.acceptable:
                return revised
        return plan.fallback_response or cls.fallback(founder_message, mode, context)

    @staticmethod
    def fallback(founder_message: str, mode: str, context: dict[str, Any]) -> str:
        normalized = " ".join(founder_message.lower().split()).strip(" .!")
        if normalized in {"approve", "approved", "go ahead", "proceed", "proceed with this", "create the mission"}:
            return "I do not have a pending decision-ready mission in this conversation. Tell me which recommendation you want to approve, or ask me to prepare one first."
        return (
            "I cannot produce a reliable answer from the available evidence right now. "
            "I can continue once the relevant read-only context or provider response is available."
        )
