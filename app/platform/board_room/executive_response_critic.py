from __future__ import annotations

import re
from dataclasses import dataclass


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
    def evaluate(cls, draft: str, *, mode: str, founder_message: str) -> ResponseQuality:
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
        return ResponseQuality(
            acceptable=not signals,
            signals=tuple(signals),
            revision_instruction="Rewrite as a direct, evidence-aware answer without internal mechanics or an unrequested workflow." if signals else "",
        )
