from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.platform.board_room.conversation_mode import ACTION_MODES, CONVERSATIONAL_MODES


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

    MODE_TO_CONTRACT = {
        "direct_answer": "INFORMATION_REQUEST",
        "explanation": "INFORMATION_REQUEST",
        "capability_query": "CAPABILITY_DESCRIPTION",
        "limitation_query": "CAPABILITY_DESCRIPTION",
        "capability_comparison": "CAPABILITY_COMPARISON",
        "competitive_comparison": "CAPABILITY_COMPARISON",
        "architecture_explanation": "ARCHITECTURE_EXPLANATION",
        "architecture_review": "ARCHITECTURE_REVIEW",
        "architecture_recommendation": "STRATEGIC_ADVICE",
        "status_request": "STATUS_REQUEST",
        "product_discovery": "PRODUCT_DISCOVERY",
        "product_review": "STRATEGIC_ADVICE",
        "system_review": "SYSTEM_REVIEW",
        "brainstorming": "BRAINSTORMING",
        "executive_discussion": "STRATEGIC_ADVICE",
        "strategic_advice": "STRATEGIC_ADVICE",
        "technical_diagnosis": "TROUBLESHOOTING",
        "conversational_follow_up": "CONVERSATIONAL_FOLLOW_UP",
        "implementation_planning": "EXECUTION_REQUEST",
        "mission_recommendation": "PROJECT_PLANNING",
        "mission_approval": "EXECUTION_REQUEST",
        "execution_command": "EXECUTION_REQUEST",
        "implementation_handoff": "EXECUTION_REQUEST",
        "mission_preparation": "EXECUTION_REQUEST",
        "informational_capability_query": "CAPABILITY_DESCRIPTION",
    }

    @classmethod
    def classify(
        cls,
        message: str,
        *,
        response_mode: str,
        decomposition: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> ConversationContract:
        requested = str(decomposition.get("requested_action") or "QUESTION")
        family = cls.MODE_TO_CONTRACT.get(response_mode)
        if family is None:
            family = "INFORMATION_REQUEST"
        if requested == "GOVERNED_ACTION":
            family = "EXECUTION_REQUEST"
        return cls._contract(family)

    @staticmethod
    def _contract(mode: str, outcome: str = "", governed: bool = False) -> ConversationContract:
        source_map = {
            "PRODUCT_DISCOVERY": ["company_memory", "repository_intelligence", "architecture_graph", "organisation", "imported_repositories"],
            # "organisation" (the agent roster + each agent's documented skills.md
            # capabilities) is real, relevant context here - a founder asking Jarvis to
            # evaluate, compare, or discuss the AI workforce's actual skills needs this to
            # answer from real data instead of guessing. This is the source_map actually
            # wired into the real request path (operating_console/service.py passes
            # `selected_sources=set(contract.context_sources)` on every call, never None) -
            # a prior fix added "organisation" to ContextRetriever._source_names() instead,
            # which is never reached from real traffic because selected_sources is never
            # None there, so it had zero effect on what Jarvis actually saw.
            "STRATEGIC_ADVICE": ["executive_intelligence", "company_memory", "repository_intelligence", "architecture_graph", "organisation"],
            "BRAINSTORMING": ["company_memory"],
            "SYSTEM_REVIEW": ["executive_intelligence", "company_memory", "mission_history", "repository_intelligence", "architecture_graph"],
            "ARCHITECTURE_EXPLANATION": ["executive_intelligence", "repository_intelligence", "architecture_graph"],
            "ARCHITECTURE_REVIEW": ["executive_intelligence", "repository_intelligence", "architecture_graph"],
            "CAPABILITY_DESCRIPTION": ["executive_intelligence", "repository_intelligence", "organisation", "cognitive_memory", "imported_repositories"],
            "CAPABILITY_COMPARISON": ["executive_intelligence", "repository_intelligence", "organisation"],
            "STATUS_REQUEST": ["executive_intelligence", "mission_history"],
            "TROUBLESHOOTING": ["executive_intelligence", "mission_history", "repository_intelligence", "architecture_graph"],
            "PROJECT_PLANNING": ["company_memory", "repository_intelligence", "engineering_capacity"],
            "EXECUTION_REQUEST": ["executive_intelligence", "mission_history", "repository_intelligence", "engineering_capacity", "organisation", "cognitive_memory", "imported_repositories"],
            "CONVERSATIONAL_FOLLOW_UP": ["company_memory"],
            "INFORMATION_REQUEST": [],
        }
        requirement_map = {
            "PRODUCT_DISCOVERY": ["target user", "priority scope", "commercial rationale", "trade-offs", "next step"],
            "STRATEGIC_ADVICE": ["recommendation", "rationale", "trade-offs", "next step"],
            "BRAINSTORMING": ["distinct ideas", "useful differences", "uncertainty"],
            "SYSTEM_REVIEW": ["verified strengths", "verified weaknesses", "recommendation"],
            "ARCHITECTURE_EXPLANATION": ["verified architecture", "authority boundaries", "known limitations"],
            "ARCHITECTURE_REVIEW": ["verified architecture", "observations", "uncertainty"],
            "CAPABILITY_DESCRIPTION": ["verified capabilities", "governance limits", "uncertainty"],
            "CAPABILITY_COMPARISON": ["requested entities", "comparison dimensions", "table", "balanced self-assessment", "uncertainty"],
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
            "BRAINSTORMING": [],
            "SYSTEM_REVIEW": ["DECISION", "ACTION", "KNOWLEDGE"],
            "ARCHITECTURE_EXPLANATION": ["KNOWLEDGE"],
            "ARCHITECTURE_REVIEW": ["KNOWLEDGE"],
            "CAPABILITY_DESCRIPTION": ["KNOWLEDGE"],
            "CAPABILITY_COMPARISON": ["KNOWLEDGE"],
            "STATUS_REQUEST": [],
            "TROUBLESHOOTING": ["DECISION", "ACTION"],
            "PROJECT_PLANNING": ["DECISION", "ACTION", "MISSION_PROPOSAL"],
            "EXECUTION_REQUEST": ["ACTION", "MISSION_PROPOSAL"],
            "CONVERSATIONAL_FOLLOW_UP": ["DECISION", "ACTION"],
            "INFORMATION_REQUEST": [],
        }
        outcome_map = {
            "PRODUCT_DISCOVERY": "Define the customer, first product, commercial case, and next learning step",
            "STRATEGIC_ADVICE": "Make a decision-ready recommendation",
            "BRAINSTORMING": "Explore distinct possibilities without initiating action",
            "SYSTEM_REVIEW": "Assess the current AI Software Factory system",
            "ARCHITECTURE_EXPLANATION": "Explain the current platform architecture from verified evidence",
            "ARCHITECTURE_REVIEW": "Review current architecture without prescribing work",
            "CAPABILITY_DESCRIPTION": "Describe current capabilities and limits",
            "CAPABILITY_COMPARISON": "Compare the requested systems without making a choice for the founder",
            "STATUS_REQUEST": "Report current operational state",
            "TROUBLESHOOTING": "Identify the likely cause and first corrective step",
            "PROJECT_PLANNING": "Create a plan without execution",
            "EXECUTION_REQUEST": "Prepare or perform a consequential action under governance",
            "CONVERSATIONAL_FOLLOW_UP": "Continue the explicitly referenced prior topic",
            "INFORMATION_REQUEST": "Answer the founder's question directly",
        }
        governed = mode == "EXECUTION_REQUEST"
        return ConversationContract(
            mode=mode,
            requested_outcome=outcome or outcome_map[mode],
            context_sources=source_map[mode],
            governance_required=governed,
            approval_may_be_required=governed,
            response_requirements=requirement_map[mode],
            permissible_artifacts=artifact_map[mode],
        )

    @classmethod
    def registered_modes_are_explicit(cls) -> bool:
        return (CONVERSATIONAL_MODES | ACTION_MODES) <= set(cls.MODE_TO_CONTRACT)
