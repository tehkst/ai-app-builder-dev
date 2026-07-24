from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.platform.board_room.executive_intelligence_orchestrator import (
    ExecutiveIntelligenceOrchestrator,
)
from app.platform.board_room.executive_response_critic import ExecutiveResponseCritic
from app.platform.board_room.founder_conversation_contract import (
    ConversationContract,
    FounderConversationContract,
)
from app.platform.board_room.founder_response_composer import FounderResponseComposer
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
        contract: Optional[ConversationContract] = None,
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        return cls.respond_with_outcome(
            founder_message=founder_message,
            mode=mode,
            context=context,
            invoke=invoke,
            decomposition=decomposition,
            provider=provider,
            model=model,
            contract=contract,
            conversation_history=conversation_history,
        )["text"]

    @classmethod
    def respond_with_outcome(
        cls,
        *,
        founder_message: str,
        mode: str,
        context: dict[str, Any],
        invoke: Callable[[dict[str, Any]], dict[str, Any]],
        decomposition: Optional[dict[str, Any]] = None,
        provider: Any = None,
        model: Any = None,
        contract: Optional[ConversationContract] = None,
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        contract = contract or FounderConversationContract.classify(
            founder_message,
            response_mode=mode,
            decomposition=decomposition or {},
            conversation_history=conversation_history,
        )
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
        provider_error = ""
        try:
            result = invoke(payload)
        except Exception as exc:
            result = {"status": "failed", "output_text": ""}
            provider_error = type(exc).__name__
        provider_unavailable = str(result.get("status") or "").lower() in {
            "failed", "error", "missing-secret", "unavailable",
        }
        draft = str(result.get("output_text") or "").strip()
        quality = ExecutiveResponseCritic.evaluate(
            draft,
            mode=mode,
            founder_message=founder_message,
            executive_brief=plan.executive_brief,
        )
        if quality.acceptable:
            selected = draft
        else:
            selected = ""
        if not quality.acceptable and draft and plan.uses_decision_engine:
            try:
                revision = invoke({
                    **payload,
                    "prompt": payload["prompt"]
                    + "\n\nDraft to revise:\n"
                    + draft
                    + "\n\nBounded revision instruction:\n"
                    + quality.revision_instruction,
                })
            except Exception as exc:
                revision = {"status": "failed", "output_text": ""}
                provider_error = type(exc).__name__
            revised = str(revision.get("output_text") or "").strip()
            revised_quality = ExecutiveResponseCritic.evaluate(
                revised,
                mode=mode,
                founder_message=founder_message,
                executive_brief=plan.executive_brief,
            )
            if revised_quality.acceptable:
                selected = revised
        response = FounderResponseComposer.compose(
            founder_message=founder_message,
            draft=selected,
            contract=contract,
            context=context,
            executive_brief=plan.executive_brief,
            conversation_history=conversation_history,
        )
        text = response.text
        if provider_unavailable:
            text = (
                "The AI provider is temporarily unavailable, so I am using the verified "
                "context already available to keep this discussion moving:\n\n"
                + text
            )
        return {
            "text": text,
            "decisions": response.decisions,
            "actions": response.actions,
            "mission_proposals": response.mission_proposals,
            "knowledge": response.knowledge,
            "validation": response.validation,
            "fallback_used": response.fallback_used,
            "capabilities_invoked": ["AFOS-009", "AFOS-010"],
            "error_category": provider_error or "none",
        }

    @staticmethod
    def fallback(founder_message: str, mode: str, context: dict[str, Any]) -> str:
        normalized = " ".join(founder_message.lower().split()).strip(" .!")
        if normalized in {"approve", "approved", "go ahead", "proceed", "proceed with this", "create the mission"}:
            return "I do not have a pending decision-ready mission in this conversation. Tell me which recommendation you want to approve, or ask me to prepare one first."
        return (
            "I cannot produce a reliable answer from the available evidence right now. "
            "I can continue once the relevant read-only context or provider response is available."
        )
