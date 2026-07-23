from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConversationContract:
    mode: str
    requested_outcome: str
    context_sources: List[str]
    governance_required: bool
    approval_may_be_required: bool
    response_requirements: List[str]
    permissible_artifacts: List[str]


class FounderConversationContract:
    """Classifies founder interaction without owning reasoning or execution."""

    @classmethod
    def classify(
        cls,
        message: str,
        *,
        response_mode: str,
        decomposition: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> ConversationContract:
        text = " ".join(message.lower().split())
        requested = str(decomposition.get("requested_action") or "QUESTION")
        history = conversation_history or []

        if cls._product_discovery(text, requested):
            return cls._contract("PRODUCT_DISCOVERY", "Define the customer, first product, commercial case, and next learning step", False)
        if requested == "GOVERNED_ACTION" or response_mode == "execution_command":
            return cls._contract("EXECUTION_REQUEST", "Perform a consequential action", True)
        if requested == "IMPLEMENT" or response_mode in {"implementation_planning", "implementation_handoff"}:
            return cls._contract("EXECUTION_REQUEST", "Prepare implementation for governed execution", True)
        if response_mode == "status_request" or re.search(r"\b(?:current status|where are we|progress)\b", text):
            return cls._contract("STATUS_REQUEST", "Report current operational state", False)
        if cls._system_review(text):
            return cls._contract("SYSTEM_REVIEW", "Assess the current AI Software Factory system", False)
        if history and cls._follow_up(text):
            return cls._contract("CONVERSATIONAL_FOLLOW_UP", "Continue the existing decision", False)
        if cls._strategic_question(text):
            return cls._contract("STRATEGIC_ADVICE", "Make a decision-ready recommendation", False)
        if response_mode == "technical_diagnosis":
            return cls._contract("TROUBLESHOOTING", "Identify the likely cause and first corrective step", False)
        if requested == "PLAN":
            return cls._contract("PROJECT_PLANNING", "Create a plan without execution", False)
        if (
            response_mode in {"strategic_advice", "executive_discussion"}
            or requested in {"COMPARE", "RECOMMEND"}
        ):
            return cls._contract("STRATEGIC_ADVICE", "Make a decision-ready recommendation", False)
        if response_mode in {"direct_answer", "explanation", "capability_query", "limitation_query"}:
            return cls._contract("INFORMATION_REQUEST", "Answer the founder's question directly", False)
        return cls._contract("STRATEGIC_ADVICE", "Provide useful executive advice", False)

    @staticmethod
    def _contract(mode: str, outcome: str, governed: bool) -> ConversationContract:
        source_map = {
            "PRODUCT_DISCOVERY": ["company_memory"],
            "STRATEGIC_ADVICE": ["company_memory"],
            "SYSTEM_REVIEW": ["executive_intelligence", "company_memory", "mission_history", "repository_intelligence"],
            "STATUS_REQUEST": ["executive_intelligence", "mission_history"],
            "TROUBLESHOOTING": ["executive_intelligence", "mission_history", "repository_intelligence"],
            "PROJECT_PLANNING": ["company_memory", "repository_intelligence", "engineering_capacity"],
            "EXECUTION_REQUEST": ["executive_intelligence", "mission_history", "repository_intelligence", "engineering_capacity"],
            "CONVERSATIONAL_FOLLOW_UP": ["company_memory"],
            "INFORMATION_REQUEST": [],
        }
        requirement_map = {
            "PRODUCT_DISCOVERY": ["target user", "priority scope", "commercial rationale", "trade-offs", "next step"],
            "STRATEGIC_ADVICE": ["recommendation", "rationale", "trade-offs", "next step"],
            "SYSTEM_REVIEW": ["verified strengths", "verified weaknesses", "recommendation"],
            "STATUS_REQUEST": ["relevant verified status", "unknowns", "next step"],
            "TROUBLESHOOTING": ["likely cause", "evidence", "first intervention"],
            "PROJECT_PLANNING": ["scope", "sequence", "risks", "next step"],
            "EXECUTION_REQUEST": ["requested outcome", "approval boundary", "safe next action"],
            "CONVERSATIONAL_FOLLOW_UP": ["continuity", "direct answer", "next step"],
            "INFORMATION_REQUEST": ["direct answer"],
        }
        artifact_map = {
            "PRODUCT_DISCOVERY": ["DECISION", "ACTION", "MISSION_PROPOSAL"],
            "STRATEGIC_ADVICE": ["DECISION", "ACTION"],
            "SYSTEM_REVIEW": ["DECISION", "ACTION", "KNOWLEDGE"],
            "STATUS_REQUEST": ["ACTION"],
            "TROUBLESHOOTING": ["DECISION", "ACTION"],
            "PROJECT_PLANNING": ["DECISION", "ACTION", "MISSION_PROPOSAL"],
            "EXECUTION_REQUEST": ["ACTION", "MISSION_PROPOSAL"],
            "CONVERSATIONAL_FOLLOW_UP": ["DECISION", "ACTION"],
            "INFORMATION_REQUEST": [],
        }
        return ConversationContract(
            mode=mode,
            requested_outcome=outcome,
            context_sources=source_map[mode],
            governance_required=governed,
            approval_may_be_required=governed,
            response_requirements=requirement_map[mode],
            permissible_artifacts=artifact_map[mode],
        )

    @staticmethod
    def _product_discovery(text: str, requested: str) -> bool:
        product_terms = (
            "crm", "management system", "customer portal", "app", "software",
            "first version", "mvp", "target user", "commercially attractive",
        )
        discovery_terms = (
            "want to build", "should include", "who the target", "what should we build",
            "build me", "first version", "product",
        )
        return (
            requested != "GOVERNED_ACTION"
            and any(term in text for term in product_terms)
            and any(term in text for term in discovery_terms)
        )

    @staticmethod
    def _system_review(text: str) -> bool:
        return "ai software factory" in text and any(
            term in text for term in ("review", "current state", "strongest", "weakest", "focus on")
        )

    @staticmethod
    def _strategic_question(text: str) -> bool:
        return bool(re.search(
            r"\b(?:how should|what should|why should).*(?:compete|prioriti[sz]e|choose|position|differentiate|instead)\b",
            text,
        ))

    @staticmethod
    def _follow_up(text: str) -> bool:
        return len(text.split()) < 14 or bool(
            re.search(r"\b(?:it|that|this|we|they|what should we|which one|next)\b", text)
        )
