from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


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
        executive_brief: dict[str, Any] | None = None,
    ) -> ResponseQuality:
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
        brief = executive_brief or {}
        if brief:
            if not cls._meaningfully_reflects(draft, str(brief.get("recommended_position") or "")):
                signals.append("position_not_established")
            strategy = str(brief.get("strategy") or "")
            if strategy in {"COMPARE", "PRIORITISE", "ROADMAP", "ARCHITECTURE_REVIEW"}:
                tradeoff = str(brief.get("decisive_tradeoff") or "")
                has_contrast = bool(re.search(r"\b(?:but|while|versus|trade-?off|sacrifice|instead)\b", lowered))
                if not has_contrast and not cls._meaningfully_reflects(draft, tradeoff):
                    signals.append("decisive_tradeoff_missing")
            evidence = brief.get("verified_evidence") or []
            evidence_text = " ".join(
                str(item.get("fact") or "") for item in evidence if isinstance(item, dict)
            )
            if evidence_text and not cls._meaningfully_reflects(draft, evidence_text):
                signals.append("verified_evidence_not_used")
            if brief.get("unknowns") and not re.search(
                r"\b(?:unknown|uncertain|insufficient|not available|cannot verify|inference)\b",
                lowered,
            ):
                signals.append("uncertainty_not_acknowledged")
            if len(draft.split()) > 260:
                signals.append("excessive_verbosity")
        return ResponseQuality(
            acceptable=not signals,
            signals=tuple(signals),
            revision_instruction=(
                "Rewrite once as a concise founder-facing answer. Answer the request, take the supported position, "
                "state the decisive trade-off, distinguish evidence from inference and unknowns, connect the recommendation "
                "to founder consequences, and do not expose internal data or propose an unrequested mission. Quality signals: "
                + ", ".join(signals)
            ) if signals else "",
        )

    @staticmethod
    def _meaningfully_reflects(draft: str, reference: str) -> bool:
        stop = {
            "about", "after", "again", "also", "because", "before", "being",
            "could", "from", "have", "into", "more", "should", "that", "their",
            "there", "these", "this", "through", "with", "would",
        }
        draft_words = {
            word for word in re.findall(r"[a-z][a-z-]{3,}", draft.lower()) if word not in stop
        }
        reference_words = {
            word for word in re.findall(r"[a-z][a-z-]{3,}", reference.lower()) if word not in stop
        }
        if not reference_words:
            return True
        required = 1 if len(reference_words) < 5 else 2
        return len(draft_words & reference_words) >= required
