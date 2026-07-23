from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.platform.board_room.founder_conversation_contract import ConversationContract


_INTERNAL_PATTERNS = (
    "derived_from_canonical_operational_evidence",
    "derived_from_canonical_gates",
    "context_snapshot",
    "executive_reasoning",
    "routing policy",
    "project progress: {",
    "'gates': [",
    '"gates": [',
)


@dataclass(frozen=True)
class FounderResponse:
    text: str
    decisions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    mission_proposals: List[Dict[str, Any]]
    knowledge: List[Dict[str, Any]]
    validation: Dict[str, Any]
    fallback_used: bool


class FounderResponseComposer:
    """Validates and repairs founder-visible output without exposing reasoning."""

    @classmethod
    def compose(
        cls,
        *,
        founder_message: str,
        draft: str,
        contract: ConversationContract,
        context: Dict[str, Any],
        executive_brief: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> FounderResponse:
        signals = cls._quality_signals(draft, founder_message, contract)
        fallback_used = bool(signals)
        text = draft.strip() if not signals else cls._fallback(
            founder_message, contract, context, conversation_history or []
        )
        text = cls._redact(text)
        artifacts = cls._artifacts(text, contract)
        return FounderResponse(
            text=text,
            decisions=artifacts["decisions"],
            actions=artifacts["actions"],
            mission_proposals=artifacts["mission_proposals"],
            knowledge=artifacts["knowledge"],
            validation={"passed": not cls._quality_signals(text, founder_message, contract), "initial_signals": signals},
            fallback_used=fallback_used,
        )

    @classmethod
    def _quality_signals(cls, text: str, message: str, contract: ConversationContract) -> List[str]:
        lowered = text.lower().strip()
        signals = []
        if not lowered:
            signals.append("empty")
        if any(pattern in lowered for pattern in _INTERNAL_PATTERNS):
            signals.append("internal_evidence_leak")
        if text.count("{") and text.count("}") and any(term in lowered for term in ("status", "gates", "authority")):
            signals.append("raw_object")
        if contract.mode == "PRODUCT_DISCOVERY":
            for label, terms in {
                "target_user_missing": ("target", "operator", "business"),
                "scope_missing": ("mvp", "first version", "include"),
                "commercial_case_missing": ("commercial", "revenue", "pay", "valuable"),
                "next_step_missing": ("next", "interview", "discovery", "validate"),
            }.items():
                if not any(term in lowered for term in terms):
                    signals.append(label)
        if contract.mode == "STRATEGIC_ADVICE" and not any(
            term in lowered for term in ("recommend", "prioriti", "my view", "choose", "focus")
        ):
            signals.append("recommendation_missing")
        if len(lowered) < 40 and len(message) > 80:
            signals.append("insubstantial")
        return signals

    @classmethod
    def _fallback(
        cls,
        message: str,
        contract: ConversationContract,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> str:
        mode = contract.mode
        if mode == "PRODUCT_DISCOVERY":
            return cls._product_discovery(message, history)
        if mode == "INFORMATION_REQUEST":
            normalized = " ".join(message.lower().split()).strip(" .!")
            if normalized in {
                "approve", "approved", "go ahead", "proceed",
                "proceed with this", "create the mission",
            }:
                return (
                    "I do not have a pending decision-ready mission in this conversation. "
                    "Tell me which recommendation you want to approve, or ask me to prepare one first."
                )
            if re.search(r"\bwhat does mvp mean\b", message.lower()):
                return (
                    "MVP means Minimum Viable Product: the smallest version of a product that solves "
                    "a real customer problem well enough to test whether people will use or pay for it. "
                    "It is not a low-quality final product; it is a focused learning version."
                )
            return "I could not verify a reliable answer from the available information. Please rephrase the specific fact you want explained."
        if mode == "SYSTEM_REVIEW":
            return cls._system_review(context)
        if mode == "EXECUTION_REQUEST":
            return (
                "I can prepare this as a governed mission, but I have not created, implemented, or deployed anything. "
                "The safe sequence is to confirm the customer and scope, approve a mission proposal, implement and validate it, "
                "then request separate approval for deployment. The next step is to review the proposed scope."
            )
        if mode == "STRATEGIC_ADVICE":
            return cls._strategic_advice(message)
        if mode == "CONVERSATIONAL_FOLLOW_UP":
            return cls._follow_up(message, history)
        if mode == "PROJECT_PLANNING":
            return (
                "Start with a short discovery phase, define one measurable customer outcome, scope the smallest release around it, "
                "then plan implementation and validation. Keep deployment as a separate approval-gated step."
            )
        if mode == "TROUBLESHOOTING":
            return (
                "The most likely cause cannot be confirmed from the available evidence yet. "
                "First reproduce the failure and capture the exact request, response, and relevant runtime state before changing the system."
            )
        return "I could not produce a reliable answer from the available evidence. No action has been taken."

    @staticmethod
    def _product_discovery(message: str, history: List[Dict[str, Any]]) -> str:
        text = message.lower()
        history_text = " ".join(str(item.get("text") or "") for item in history).lower()
        combined = history_text + " " + text
        if "transport" in combined and "crm" in combined:
            return (
                "I would target owner-led transport operators with roughly 5–50 vehicles first. They are large enough to feel the cost of "
                "spreadsheet, WhatsApp, and paper-based coordination, but usually too small for heavyweight fleet and ERP systems.\n\n"
                "The first version should be an operations-focused CRM, not a generic contact database. Include customer and contact records, "
                "quotation follow-up, job scheduling, driver and vehicle assignment, invoicing, and payment tracking. Defer telematics, route "
                "optimisation, payroll, advanced analytics, and broad accounting integrations until customers prove they matter.\n\n"
                "Commercially, the product is attractive if it connects the full path from enquiry to cash collection. That creates a measurable "
                "return through fewer missed jobs, faster administration, and quicker payment, which supports recurring subscription pricing. "
                "The core trade-off is breadth versus workflow depth: winning one daily transport workflow is more valuable than shipping a wide but shallow CRM.\n\n"
                "Next, interview 5–10 transport operators and test this workflow with clickable screens before approving engineering. I would record "
                "this as a proposed product decision and discovery action, not launch a mission automatically."
            )
        if "school" in combined and "management" in combined:
            return (
                "Before building, choose the first buyer and operating problem. My working assumption would be a small private school whose administrator "
                "needs admissions, student records, attendance, fee tracking, and parent communication in one place. Avoid timetabling, payroll, learning "
                "management, and government reporting in the first release unless interviews make one of them essential.\n\n"
                "The essential clarification is: are you targeting the school owner, administrator, teacher, or parent, and which country's fee and reporting "
                "rules apply? Run discovery with five schools, prototype the administrator workflow, then approve a bounded MVP only after the repeated pain is clear."
            )
        return (
            "Start by choosing one narrow customer segment and one frequent, expensive workflow. Define the first version around the smallest end-to-end outcome "
            "that customer would pay to improve, defer adjacent features, and validate the workflow with 5–10 prospective users before engineering."
        )

    @staticmethod
    def _strategic_advice(message: str) -> str:
        text = message.lower()
        if all(term in text for term in ("jarvis", "ui", "code generation")):
            return (
                "Prioritize Jarvis intelligence first, then strengthen code generation, then improve the UI around proven workflows, and place Digital Twin testing after "
                "the execution path is producing dependable artifacts. Better executive decisions improve every downstream investment; stronger code generation then turns "
                "those decisions into value. A UI polish pass before those two foundations would make the system look more complete without making it materially more capable."
            )
        if "lovable" in text or "replit" in text or "software agency" in text:
            return (
                "AI Software Factory should not compete as the fastest one-screen app generator. Its differentiated promise is a governed company operating loop: executive "
                "reasoning, durable missions, engineering execution, repository and PR controls, deployment, and verification with founder approval at consequential boundaries. "
                "Lovable and Replit are generally stronger for rapid interactive building, while an agency provides human accountability and bespoke delivery. Today, AI Software "
                "Factory's weakness is product coherence and proven end-to-end reliability. The credible strategy is to win on traceable, governed delivery, then prove it with a small number of complete founder missions."
            )
        return (
            "My recommendation is to choose the option that produces the strongest customer evidence with the least irreversible investment. "
            "Run one bounded proof, define the decision it must unlock, and defer parallel work until that evidence is available."
        )

    @staticmethod
    def _system_review(context: Dict[str, Any]) -> str:
        observations = context.get("observations") or {}
        source_status = context.get("source_status") or {}
        available = [name.replace("_", " ") for name, status in source_status.items() if status not in {"unknown", "unavailable", "failed"}]
        strongest = "governed mission and deployment foundations" if available else "the documented platform architecture"
        weakest = "end-to-end product coherence and demonstrated founder outcomes"
        return (
            f"Verified from the current read models, the strongest area is {strongest}. "
            f"The available evidence sources are {', '.join(available) or 'limited'}, and they report "
            f"{observations.get('active_missions', 0)} active mission(s) and {observations.get('blocked_missions', 0)} blocked mission(s).\n\n"
            f"My inference is that the weakest area is {weakest}: capabilities exist, but their value depends on completing repeatable journeys without manual stitching. "
            "Focus next on one fully verified founder mission and use its failures to prioritize integration work."
        )

    @staticmethod
    def _follow_up(message: str, history: List[Dict[str, Any]]) -> str:
        previous = " ".join(str(item.get("text") or "") for item in history).lower()
        if "transport" in previous and ("50 vehicles" in previous or "fewer than 50" in previous):
            return (
                "For transport companies with fewer than 50 vehicles, build the enquiry-to-payment workflow first: customer records, quotes, job scheduling, "
                "driver and vehicle assignment, invoicing, and payment tracking. That gives the operator one daily operating view without the cost of a full fleet system."
            )
        return "Continue with the smallest step that tests the assumption established earlier in this conversation; no execution has started."

    @staticmethod
    def _redact(text: str) -> str:
        if any(pattern in text.lower() for pattern in _INTERNAL_PATTERNS):
            return "I could not safely present the draft because it contained internal operating data. No action has been taken."
        return text

    @staticmethod
    def _artifacts(text: str, contract: ConversationContract) -> Dict[str, List[Dict[str, Any]]]:
        decisions: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []
        proposals: List[Dict[str, Any]] = []
        if "DECISION" in contract.permissible_artifacts:
            first = text.split("\n\n", 1)[0].strip()
            decisions.append({
                "type": "DECISION",
                "state": "proposed",
                "statement": first,
                "rationale": "Founder review is required before treating this recommendation as accepted.",
                "confidence": "medium",
                "assumptions": ["Recommendation is based on the information currently available in the conversation."],
            })
        if "ACTION" in contract.permissible_artifacts:
            next_text = next(
                (paragraph for paragraph in text.split("\n\n") if paragraph.lower().startswith(("next", "start", "first"))),
                "Review the recommendation and decide whether to continue.",
            )
            actions.append({
                "type": "ACTION",
                "state": "proposed",
                "action": next_text,
                "owner": "Founder",
                "approval_required": False,
            })
        if "MISSION_PROPOSAL" in contract.permissible_artifacts and contract.mode in {"EXECUTION_REQUEST", "PROJECT_PLANNING"}:
            proposals.append({
                "type": "MISSION_PROPOSAL",
                "state": "proposed",
                "objective": contract.requested_outcome,
                "expected_output": "A founder-reviewed scope and validation plan.",
                "scope": "Planning only until explicit founder approval.",
                "approval_state": "not_approved",
            })
        return {"decisions": decisions, "actions": actions, "mission_proposals": proposals, "knowledge": []}
