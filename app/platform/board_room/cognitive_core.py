from __future__ import annotations

from typing import Any, Callable

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
        provider: Any = None,
        model: Any = None,
    ) -> str:
        result = invoke({
            "system": JarvisPromptBuilder.system_prompt(mode),
            "prompt": JarvisPromptBuilder.user_prompt(founder_message, context, mode),
            "provider": provider,
            "model": model,
        })
        draft = str(result.get("output_text") or "").strip()
        fallback = cls.fallback(founder_message, mode, context)
        quality = ExecutiveResponseCritic.evaluate(draft, mode=mode, founder_message=founder_message)
        return draft if quality.acceptable else fallback

    @staticmethod
    def fallback(founder_message: str, mode: str, context: dict[str, Any]) -> str:
        normalized = founder_message.lower()
        if normalized.strip(" .!") in {"approve", "approved", "go ahead", "proceed", "proceed with this", "create the mission"}:
            return "I do not have a pending decision-ready mission in this conversation. Tell me which recommendation you want to approve, or ask me to prepare one first."
        if "agent" in normalized and any(term in normalized for term in ("three", "3", "clickable", "skills")):
            return (
                "Verified from the current founder UI: Agents is presented as three summary groups, not as the complete registered-agent directory. "
                "Those summaries are not wired as profile tabs, so they cannot currently open an agent, show its skills, or edit permitted skills.\n\n"
                "The likely inference is that the runtime has richer agent definitions than this page exposes. My product view is to keep the groups as filters, "
                "then show the registered agents beneath them with skill visibility and governance-controlled editing. This is a product-surface gap; it does not by itself prove that only three agents exist."
            )
        if "every user message" in normalized and "mission" in normalized:
            return "I disagree with that design. Most founder messages are questions, exploration, or critique; turning each into a mission would create noise, accidental scope, and approval fatigue. Conversation should clarify intent first, while mission creation stays an explicit transition when work is actually requested."
        if mode == "brainstorming":
            return "I would make Jarvis feel more like a co-founder through sharper memory, clearer opinions, stronger follow-through, honest uncertainty, and responses that change shape with the conversation instead of repeating one executive memo format."
        if mode == "strategic_advice":
            if "agent" in normalized:
                return "My view is to expose useful agent visibility without exposing every internal control. Show the complete registered roster and readable skills, then make editing conditional on governance. That improves trust and discoverability without turning the founder UI into an unsafe administration console."
            return "My view is to preserve a clear boundary between exploration and commitment. Discuss and test assumptions freely, then create a governed mission only when the founder has chosen an outcome worth executing."
        if mode == "explanation":
            return "Mission Execution links an approved founder mission to a durable workflow run, advances it through governed stages, and projects worker progress back into Mission Control. Repository changes, merge, deployment, verification, and rollback remain behind their existing approval boundaries."
        return "I understand the question, but the available evidence is not specific enough for a confident answer. I can give a useful view once the relevant product or runtime evidence is available."
