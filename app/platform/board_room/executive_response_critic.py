from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

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
        executive_brief: dict[str, Any] | None = None,
        contract: Optional[ConversationContract] = None,
        decomposition: dict[str, Any] | None = None,
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
        family = contract.mode if contract else ""
        if family == "CAPABILITY_COMPARISON":
            signals.extend(cls._capability_comparison_signals(draft, founder_message))
        brief = executive_brief or {}
        if brief:
            # A message classified into a recommendation-shaped contract family (e.g.
            # STRATEGIC_ADVICE via "executive_discussion") is not always actually asking
            # for a recommendation - the decomposer's own requested_action distinguishes
            # "evaluate/list/map the current state" (ANALYZE) from "tell me what to do"
            # (RECOMMEND/COMPARE/PLAN). Forcing a decisive position and trade-off onto an
            # honest evaluation/audit answer was a real, reproduced bug: a founder asking
            # Jarvis to compare the agent roster against an external skill list got a
            # generic "strongest customer evidence...bounded proof" non-answer because the
            # gate demanded recommendation framing an audit answer has no reason to contain.
            requested_action = str((decomposition or {}).get("requested_action") or "")
            recommendation_required = family not in {
                "ARCHITECTURE_EXPLANATION", "ARCHITECTURE_REVIEW",
                "CAPABILITY_DESCRIPTION", "CAPABILITY_COMPARISON",
                "INFORMATION_REQUEST", "STATUS_REQUEST",
            } and requested_action != "ANALYZE"
            if recommendation_required and not cls._meaningfully_reflects(
                draft, str(brief.get("recommended_position") or "")
            ):
                signals.append("position_not_established")
            strategy = str(brief.get("strategy") or "")
            if recommendation_required and strategy in {"COMPARE", "PRIORITISE", "ROADMAP", "ARCHITECTURE_REVIEW"}:
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
                "Rewrite once as a concise founder-facing answer. Answer the request, take the supported position "
                "when the contract requires one, distinguish evidence from inference and unknowns, and do not expose "
                "internal data or propose an unrequested mission."
            )
        return guidance + " Quality signals: " + ", ".join(signals)

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
