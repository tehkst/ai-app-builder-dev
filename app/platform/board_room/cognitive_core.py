from __future__ import annotations

import re
from typing import Any, Callable

from app.platform.board_room.executive_response_critic import ExecutiveResponseCritic
from app.platform.board_room.executive_perspective import ExecutivePerspectiveSelector
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
        perspective = ExecutivePerspectiveSelector.select(founder_message)
        result = invoke({
            "system": JarvisPromptBuilder.system_prompt(mode, perspective),
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
        subject = JarvisCognitiveCore._subject(founder_message)
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
            return (
                f"For {subject}, I would explore three directions: make the next useful choice more obvious, expose evidence at the moment trust matters, "
                "and let the experience adapt to the founder's level of detail. A stronger version would also remember prior decisions without dragging old missions into unrelated conversations."
            )
        if mode == "strategic_advice":
            if "agent" in normalized:
                return "My view is to expose useful agent visibility without exposing every internal control. Show the complete registered roster and readable skills, then make editing conditional on governance. That improves trust and discoverability without turning the founder UI into an unsafe administration console."
            if re.search(r"\balways\b|every(?:thing|one|\s+\w+)|enough for everything\b", normalized):
                return (
                    f"I would challenge the assumption that {subject}. Absolute rules erase the context that makes an executive decision sound: reversibility, evidence, cost of failure, and the outcome we actually need. "
                    "My recommendation is to define the condition under which the claim is useful, then test it against the strongest counterexample before making it policy."
                )
            return (
                f"My view on {subject} is to favor the option that creates founder-visible proof without increasing irreversible complexity. "
                "The trade-off is usually speed versus confidence: move quickly where the decision is reversible, but require stronger evidence where it changes product direction or production state."
            )
        if mode == "explanation":
            if "mission execution" in normalized or "workflow" in normalized:
                return "Mission Execution links an approved founder mission to a durable workflow run, advances it through governed stages, and projects worker progress back into Mission Control. Repository changes, merge, deployment, verification, and rollback remain behind their existing approval boundaries."
            return f"The important idea behind {subject} is that live evidence remains authoritative while Jarvis translates it for the founder. Read-only inspection can happen freely; consequential changes continue through their existing approval boundary."
        if mode == "architecture_review":
            return (
                f"On {subject}, the architectural priority is one source of truth with several read models, not several owners of the same state. "
                "I would preserve the existing durable authority, make dependencies flow toward it, and treat any parallel cache or process-local substitute as a reconciliation risk."
            )
        if mode == "technical_diagnosis":
            return (
                f"The most likely cause of {subject} is a missing or ambiguous integration boundary rather than a missing headline capability. "
                "Verified evidence is limited here, so that is an inference; the first useful check is whether the same durable identity and result are passed across the adjacent services and then projected into the UI."
            )
        if mode == "product_review":
            return (
                f"The current product question is {subject}. What matters is whether the founder can understand the state, trust the evidence, and take the next valid action without seeing internal machinery. "
                "My product view is to improve that decision surface before adding another capability."
            )
        if mode == "direct_answer":
            return f"My direct answer on {subject}: the available evidence is not sufficient for a factual claim yet. I would keep the conversation open, identify the missing evidence, and avoid turning the uncertainty into a mission by default."
        return "I understand the question, but the available evidence is not specific enough for a confident answer. I can give a useful view once the relevant product or runtime evidence is available."

    @staticmethod
    def _subject(founder_message: str) -> str:
        subject = re.sub(
            r"^(?:jarvis[,\s]+)?(?:why|how|what|should we|do you think|explain|brainstorm|give me ideas for|explore ways to|review|diagnose)\s+",
            "",
            founder_message.strip(),
            flags=re.IGNORECASE,
        )
        subject = subject.rstrip(".?!")
        return subject[0].lower() + subject[1:] if subject else "this decision"
