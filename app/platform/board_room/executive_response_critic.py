from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.platform.board_room.founder_conversation_contract import ConversationContract


@dataclass(frozen=True)
class ResponseQuality:
    acceptable: bool
    signals: tuple[str, ...]
    revision_instruction: str


class ExecutiveResponseCritic:
    """Returns bounded quality signals, never hidden free-form reasoning."""

    _INTERNAL_TERMS = (
        "system prompt",
        "routing policy",
        "route score",
        "context snapshot",
        "executive_reasoning",
        "technical_details",
        "critic output",
    )
    _RIGID_HEADINGS = ("recommendation", "why", "context", "alternatives", "risk", "next step")

    @classmethod
    def evaluate(
        cls,
        draft: str,
        *,
        mode: str,
        founder_message: str,
        contract: Optional[ConversationContract] = None,
    ) -> ResponseQuality:
        # Deliberately narrow: only real safety/completeness properties, never a
        # business-content-shape requirement ("must take a decisive position", "must
        # state a trade-off", "must echo verified evidence back verbatim"). That wider
        # gate (position_not_established/decisive_tradeoff_missing/
        # verified_evidence_not_used/uncertainty_not_acknowledged, a recommendation_required
        # apparatus keyed on contract family) was the confirmed, repeated root cause of
        # real founder-facing bugs this platform shipped three separate narrow fixes for
        # (PR #522/#523, #525) that still didn't hold up live: a real, honest,
        # substantive LLM draft was rejected because its PHRASING didn't match an
        # expected shape, not because anything was actually wrong with it. Removing the
        # gate architecture itself, not widening its exemption list again, is the fix -
        # see jarvis_live_bug_regression_check.py for the real, reproduced evidence.
        lowered = draft.lower()
        signals: list[str] = []
        if not draft.strip() or len(draft.split()) < 8:
            signals.append("insufficient_answer")
        if any(term in lowered for term in cls._INTERNAL_TERMS) or re.search(r"\b\d{1,3}/100\b", draft):
            signals.append("internal_mechanics_exposed")
        heading_count = sum(bool(re.search(rf"(?im)^(?:#+\s*)?{re.escape(name)}\s*:?​?", draft)) for name in cls._RIGID_HEADINGS)
        if mode not in {"mission_recommendation", "implementation_planning"} and heading_count >= 3:
            signals.append("forced_executive_template")
        if mode in {"direct_answer", "explanation", "brainstorming", "product_review", "technical_diagnosis", "strategic_advice"}:
            if re.search(r"\b(?:approve mission|founder decision required|create execution mission)\b", lowered):
                signals.append("unrequested_mission")
        if founder_message.rstrip().endswith("?") and len(draft.split()) < 12:
            signals.append("question_not_answered")
        family = contract.mode if contract else ""
        if family == "CAPABILITY_COMPARISON":
            signals.extend(cls._capability_comparison_signals(draft, founder_message))
        return ResponseQuality(
            acceptable=not signals,
            signals=tuple(signals),
            revision_instruction=cls._revision_instruction(signals, family),
        )

    @classmethod
    def _capability_comparison_signals(cls, draft: str, founder_message: str) -> list[str]:
        lowered = draft.lower()
        requested = {
            match.lower().replace(" ai", "")
            for match in re.findall(
                r"\b(?:OpenAI|Claude(?: AI)?|Gemini(?: AI)?|Lovable|Replit|Codex|Jarvis)\b",
                founder_message,
                flags=re.IGNORECASE,
            )
        }
        represented = {
            name for name in requested
            if name in lowered or (name == "claude" and "claude ai" in lowered)
        }
        signals: list[str] = []
        if requested - represented:
            signals.append("requested_entities_missing")
        table_lines = [line for line in draft.splitlines() if line.strip().startswith("|")]
        if len(table_lines) < 3 or not any("---" in line for line in table_lines):
            signals.append("requested_table_missing")
        if not re.search(r"\b(?:strength|best for|suited|focus|use case|limitation|trade-off)\b", lowered):
            signals.append("comparison_dimensions_missing")
        if not re.search(r"\b(?:limit|weak|not independently|cannot verify|uncertain|no single|different jobs)\b", lowered):
            signals.append("balanced_self_assessment_missing")
        if not re.search(r"\b(?:uncertain|cannot verify|not independently|varies|current evidence|public information)\b", lowered):
            signals.append("uncertainty_missing")
        if re.search(r"\b(?:jarvis|we)\s+(?:is|are)\s+(?:the\s+)?(?:best|superior|smartest|most intelligent)\b", lowered):
            signals.append("unsupported_superiority_claim")
        return signals

    @staticmethod
    def _revision_instruction(signals: list[str], family: str) -> str:
        if not signals:
            return ""
        if family == "CAPABILITY_COMPARISON":
            guidance = (
                "Rewrite as a readable Markdown comparison table covering every requested entity. "
                "Use consistent dimensions, include a balanced Jarvis limitation, state uncertainty, "
                "and avoid unsupported winner or superiority claims."
            )
        elif family in {"ARCHITECTURE_EXPLANATION", "ARCHITECTURE_REVIEW"}:
            guidance = (
                "Rewrite as a verified architecture explanation or review. Preserve uncertainty and "
                "do not force a recommendation, decision, risk, or trade-off."
            )
        else:
            guidance = (
                "Rewrite once as a concise founder-facing answer. Answer the request directly, "
                "and do not expose internal data or propose an unrequested mission."
            )
        return guidance + " Quality signals: " + ", ".join(signals)
