from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app.platform.auth.service import require_founder
from app.platform.board_room.cognitive_core import JarvisCognitiveCore
from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.board_room.conversation_mode import CONVERSATIONAL_MODES, ConversationModeClassifier
from app.platform.board_room.executive_reasoning_engine import ExecutiveReasoningEngine
from app.platform.board_room.founder_conversation_contract import FounderConversationContract
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.board_room.specialist_dispatch import consult_matching_specialist
from app.platform.ui_ux_agent.service import propose_ui_change, resolve_target_file
from app.platform.operating_console.action_service import build_decision_ready_mission_actions, build_pending_mission_actions, dispatch_board_room_action
from app.platform.operating_console.founder_presentation import present_founder_chat
from app.platform.ci_repair.service import build_ci_repair_summary
from app.platform.code_planner.service import build_code_status
from app.platform.conversation_intelligence.service import analyze_conversation
from app.platform.founder_approval.service import approve_proposal, build_founder_approval_summary
from app.platform.founder_workflow.service import build_workflow_from_console_result
from app.platform.founder_workspace.service import build_request_intake
from app.platform.execution.orchestrator import execute_authorized_engineering_workflow, launch_approved_mission_workflow
from app.platform.engineering.change_set_service import generate_executable_change_set
from app.platform.executive_intelligence.service import build_executive_intelligence_briefing
from app.platform.founder_decision.builder import build_decision_experience
from app.platform.founder_decision.service import (
    apply_natural_language_selection,
    load_decision_experience,
    save_decision_experience,
)
from app.platform.github_execution.service import build_github_execution_summary
from app.platform.mission_execution.service import plan_mission, start_mission
from app.platform.pr_orchestration.service import build_gcp_handover_status, build_pr_orchestration_summary
from app.platform.proposal_generator.service import generate_proposal
from app.platform.repository_intelligence.service import build_repository_intelligence_summary
from app.platform.runtime.service import build_ai_provider_status, invoke_ai
from app.platform.services.board_room_agents import estimate_effort, run_board_room_deliberation


BOARD_ROOM_ROLES = ["Founder", "AI CEO", "AI CTO", "Engineering Manager", "Senior Engineer", "QA Lead", "DevOps Lead", "Product Manager"]
BOARD_ROOM_STRUCTURED_INTENTS = {
    "architecture",
    "build",
    "deploy",
    "deployment",
    "implement",
    "implementation",
    "improve",
    "mission",
    "plan",
    "planning",
    "product",
    "proposal",
    "release",
    "roadmap",
    "scope",
    "settings",
    "test",
    "ui",
    "workflow",
}
LOGGER = logging.getLogger(__name__)
FOUNDER_DECISION_MODES = {
    "PRODUCT_DISCOVERY",
    "STRATEGIC_ADVICE",
    "SYSTEM_REVIEW",
    "TROUBLESHOOTING",
    "PROJECT_PLANNING",
    "EXECUTION_REQUEST",
    "CONVERSATIONAL_FOLLOW_UP",
}


def build_operating_console_summary() -> dict[str, Any]:
    ai = build_ai_provider_status()
    return {
        "company": "AI Software Factory",
        "product": "Founder Operating Console",
        "milestone": "INT-01",
        "status": "company-intelligence-board-room-ready",
        "mode": "login-first-ai-board-room",
        "purpose": "Give the founder a Board Room that reasons from a company intelligence snapshot before making recommendations.",
        "ai_provider": {"status": ai.get("status"), "model": ai.get("model")},
        "dashboard": build_dashboard_state(),
        "board_room": build_board_room_state(),
        "endpoints": {"summary": "GET /mission-control/operating-console", "dashboard": "GET /mission-control/operating-console/dashboard", "chat": "POST /mission-control/operating-console/chat", "workflow": "POST /mission-control/operating-console/workflow", "company_intelligence": "GET /mission-control/company-intelligence"},
        "handover_status": "ready-for-company-intelligence-board-room-discussions",
    }


def build_dashboard_state() -> dict[str, Any]:
    approvals = build_founder_approval_summary()
    prs = build_pr_orchestration_summary()
    github = build_github_execution_summary()
    ci = build_ci_repair_summary()
    return {
        "tiles": [
            {"name": "Board Room", "status": "company-intelligence-ready", "endpoint": "/mission-control/operating-console/chat"},
            {"name": "Approvals", "status": str(approvals.get("status", "ready")), "endpoint": "/mission-control/approvals"},
            {"name": "Pull Requests", "status": str(prs.get("status", "ready")), "endpoint": "/mission-control/pull-requests"},
            {"name": "GitHub Executor", "status": str(github.get("status", "ready")), "endpoint": "/mission-control/github-executor"},
            {"name": "CI Repair", "status": str(ci.get("status", "ready")), "endpoint": "/mission-control/ci-repair"},
        ],
        "queues": [
            {"queue": "board_room_topics", "count": 0, "status": "ready-for-founder"},
            {"queue": "pending_approvals", "count": 0, "status": "ready"},
            {"queue": "engineering_prs", "count": 0, "status": "ready"},
            {"queue": "ci_failures", "count": 0, "status": "ready"},
        ],
        "logs": [{"time": _now(), "level": "info", "message": "AI Board Room is ready."}, {"time": _now(), "level": "info", "message": "Company Intelligence snapshot is injected into Board Room prompts."}],
    }


def build_board_room_state() -> dict[str, Any]:
    return {
        "status": "company-intelligence-board-room-ready",
        "roles": BOARD_ROOM_ROLES,
        "default_agenda": ["Clarify founder intent", "Review Company Intelligence snapshot before opinions", "Identify existing capabilities before building new ones", "Separate known facts from unverified assumptions", "Recommend reuse or consolidation", "Create proposal only after architectural review", "Keep all execution behind founder approval"],
        "primary_endpoint": "POST /mission-control/operating-console/chat",
    }


def board_room_chat(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False, "message": "Please login to Mission Control before entering the Board Room."}
    message = str(payload.get("message") or payload.get("prompt") or "").strip()
    if not message:
        return {"status": "invalid-request", "error": "message is required"}
    meeting_id = str(payload.get("meeting_id") or _id("BOARD", _now(), {"message": message}))
    pending_approval = payload.get("pending_approval") if isinstance(payload.get("pending_approval"), dict) else None
    history = payload.get("conversation_history")
    if not isinstance(history, list):
        history = []
    intent = _classify_board_room_intent(
        message,
        pending_approval=pending_approval,
        conversation_history=history,
    )
    if intent.get("response_mode") == "mission_approval":
        return dispatch_board_room_action({"token": payload.get("token"), **(pending_approval or {})})
    if intent.get("response_mode") == "implementation_handoff" and resolve_target_file(message):
        return _ui_ux_proposal_response(payload, message, meeting_id)
    if intent.get("intent") == "mission_creation":
        if not isinstance(intent.get("action_metadata"), dict):
            intent["action_metadata"] = _mission_preparation_actions(
                message,
                provider=payload.get("provider"),
                model=payload.get("model"),
            )
    elif intent.get("response_mode") == "implementation_handoff":
        intent["action_metadata"] = _implementation_handoff(
            message,
            _detect_milestone(message),
            bool(intent.get("founder_already_approved")),
            provider=payload.get("provider"),
            model=payload.get("model"),
        )
    if intent.get("response_mode") in CONVERSATIONAL_MODES or intent.get("response_mode") == "implementation_handoff":
        started_at = time.monotonic()
        conversation_id = str(payload.get("conversation_id") or meeting_id)
        try:
            prior_decision = load_decision_experience(conversation_id)
        except Exception:
            prior_decision = None
        if prior_decision:
            natural_selection = apply_natural_language_selection(payload, prior_decision)
            if natural_selection:
                continuation = natural_selection.get("continuation") or {}
                updated_state = natural_selection.get("decision_experience")
                return present_founder_chat(
                    status="board-room-response-ready",
                    meeting_id=meeting_id,
                    board_room_response=str(
                        continuation.get("message")
                        or "I have applied that choice to the recommendation."
                    ),
                    conversation_intelligence={
                        "mode": "Conversational Follow Up",
                        "normalized_request": message,
                        "decisions": [],
                        "actions": [],
                        "mission_proposals": [],
                        "knowledge": [],
                        "recommended_next_action": str(
                            (continuation.get("active_decision") or {}).get("question")
                            or "Review the bounded mission."
                        ),
                        "intent_type": "founder_selection",
                        "decision_experience": updated_state,
                    },
                    action_metadata={
                        "intent_type": "founder_selection",
                        "recommended_action": "Continue the conversation.",
                        "action_buttons": [],
                    },
                    governance={
                        "execution_allowed": False,
                        "proposal_required_before_execution": True,
                        "founder_approval_required": False,
                        "company_intelligence_required": False,
                    },
                    next_step=str(
                        (continuation.get("active_decision") or {}).get("question")
                        or "Review the bounded mission."
                    ),
                )
        if prior_decision:
            confirmed = [
                str(item.get("statement") or "")
                for item in prior_decision.get("assumptions") or []
                if item.get("state") in {"confirmed", "changed"}
            ]
            if confirmed:
                history = list(history) + [{
                    "role": "decision_context",
                    "text": "Accepted working assumptions: %s" % "; ".join(confirmed),
                }]
        contract = FounderConversationContract.classify(
            message,
            response_mode=str(intent["response_mode"]),
            decomposition=intent.get("request_decomposition") or {},
            conversation_history=history,
        )
        classified_at = time.monotonic()
        context = ContextRetriever().retrieve(
            message,
            decomposition=intent.get("request_decomposition"),
            conversation_mode=str(intent["response_mode"]),
            selected_sources=set(contract.context_sources),
            conversation_history=history,
        )
        context_ready_at = time.monotonic()
        if contract.mode in {"EXECUTION_REQUEST", "CAPABILITY_DESCRIPTION"}:
            specialist_result = consult_matching_specialist(message, decomposition=intent.get("request_decomposition"))
            if specialist_result:
                context["specialist_consultation"] = specialist_result
        outcome = JarvisCognitiveCore.respond_with_outcome(
            founder_message=message,
            mode=str(intent["response_mode"]),
            context=context,
            invoke=invoke_ai,
            decomposition=intent.get("request_decomposition"),
            provider=payload.get("provider"),
            model=payload.get("model"),
            contract=contract,
            conversation_history=history,
        )
        LOGGER.info(
            "founder_conversation meeting_id=%s mode=%s sources=%s capabilities=%s "
            "governance_required=%s validation_passed=%s artifacts=%s "
            "latency_classification_ms=%d latency_context_ms=%d latency_reasoning_ms=%d "
            "latency_total_ms=%d fallback=%s error_category=%s",
            meeting_id,
            contract.mode,
            ",".join(contract.context_sources) or "none",
            ",".join(outcome["capabilities_invoked"]),
            contract.governance_required,
            outcome["validation"].get("passed"),
            ",".join(
                key for key, value in (
                    ("DECISION", outcome["decisions"]),
                    ("ACTION", outcome["actions"]),
                    ("MISSION_PROPOSAL", outcome["mission_proposals"]),
                    ("KNOWLEDGE", outcome["knowledge"]),
                ) if value
            ) or "none",
            int((classified_at - started_at) * 1000),
            int((context_ready_at - classified_at) * 1000),
            int((time.monotonic() - context_ready_at) * 1000),
            int((time.monotonic() - started_at) * 1000),
            outcome["fallback_used"],
            outcome["error_category"],
        )
        next_step = (
            str(outcome["actions"][0].get("action") or "")
            if outcome["actions"]
            else "Continue the conversation."
        )
        action_metadata = (
            dict(intent.get("action_metadata") or {})
            if contract.mode == "EXECUTION_REQUEST"
            else {}
        )
        action_metadata.update({
            "intent_type": str(intent["intent"]),
            "recommended_action": str(
                action_metadata.get("recommended_action") or next_step
            ),
        })
        action_metadata.setdefault("action_buttons", [])
        decision_experience = None
        if contract.mode in FOUNDER_DECISION_MODES:
            decision_experience = build_decision_experience(
                conversation_id=conversation_id,
                founder_message=message,
                response_text=outcome["text"],
                mode=contract.mode.replace("_", " ").title(),
                decisions=outcome["decisions"],
                actions=outcome["actions"],
                mission_proposals=outcome["mission_proposals"],
                history=history,
                provider=payload.get("provider"),
                model=payload.get("model"),
            )
            if prior_decision:
                reviewed = {
                    str(item.get("id") or ""): item
                    for item in prior_decision.get("assumptions") or []
                    if item.get("state") in {"confirmed", "changed", "rejected"}
                }
                for assumption in decision_experience.get("assumptions") or []:
                    prior_assumption = reviewed.get(str(assumption.get("id") or ""))
                    if prior_assumption:
                        assumption.update({
                            "statement": prior_assumption.get("statement"),
                            "state": prior_assumption.get("state"),
                            "confidence": prior_assumption.get("confidence"),
                        })
            try:
                if (
                    prior_decision
                    and prior_decision.get("decision_id")
                    == decision_experience.get("decision_id")
                ):
                    decision_experience = prior_decision
                else:
                    save_decision_experience(decision_experience)
            except Exception as exc:
                LOGGER.warning(
                    "founder_decision_persistence_unavailable conversation_id=%s error=%s",
                    conversation_id,
                    type(exc).__name__,
                )
            LOGGER.info(
                "founder_decision_experience conversation_id=%s assumptions=%d "
                "material_assumptions=%d founder_actions=%d ai_actions=%d",
                conversation_id,
                len(decision_experience.get("assumptions") or []),
                len([
                    item for item in decision_experience.get("assumptions") or []
                    if item.get("decision_impact") == "high"
                ]),
                len([
                    item for item in decision_experience.get("actions") or []
                    if item.get("owner") == "Founder"
                ]),
                len([
                    item for item in decision_experience.get("actions") or []
                    if item.get("owner") == "Jarvis"
                ]),
            )
        return present_founder_chat(
            status="board-room-response-ready",
            meeting_id=meeting_id,
            board_room_response=outcome["text"],
            conversation_intelligence={
                "mode": contract.mode.replace("_", " ").title(),
                "normalized_request": message,
                "decisions": outcome["decisions"],
                "actions": outcome["actions"],
                "mission_proposals": outcome["mission_proposals"],
                "knowledge": outcome["knowledge"],
                "recommended_next_action": next_step,
                "intent_type": str(intent["intent"]),
                "decision_experience": decision_experience,
            },
            action_metadata=action_metadata,
            governance={
                "execution_allowed": False,
                "proposal_required_before_execution": contract.approval_may_be_required,
                "founder_approval_required": contract.governance_required,
                "company_intelligence_required": "company_memory" in contract.context_sources,
            },
            next_step=next_step,
        )
    reasoning_result = ExecutiveReasoningEngine().reason(
        _board_room_message_candidate(message),
        response_mode=str(intent["response_mode"]),
        decomposition=intent.get("request_decomposition"),
    )
    if intent["response_mode"] != "structured":
        conversational_response = reasoning_result["founder_response"]
        action_metadata = intent.get("action_metadata") if isinstance(intent.get("action_metadata"), dict) else _minimal_action_metadata(intent)
        action_metadata = dict(action_metadata)
        action_metadata["recommended_action"] = str(
            reasoning_result["reasoning"].get("next_action")
            or action_metadata.get("recommended_action")
            or intent["next_step"]
        )
        action_metadata["reason"] = str(
            (reasoning_result["reasoning"].get("recommendation") or {}).get("why") or ""
        )
        clarification = (
            {"question": str(intent["next_step"]), "requires_answer": True}
            if intent["response_mode"] == "clarify"
            else None
        )
        return present_founder_chat(
            status="board-room-response-ready",
            meeting_id=meeting_id,
            board_room_response=conversational_response,
            conversation_intelligence={
                "mode": str(intent["label"]),
                "normalized_request": str(intent["message"]),
                "decisions": [],
                "actions": [str(intent.get("next_step") or "")] if intent.get("next_step") else [],
                "knowledge": [],
                "recommended_next_action": str(intent["next_step"]),
                "intent_type": str(intent["intent"]),
            },
            action_metadata=action_metadata,
            governance={"execution_allowed": False, "proposal_required_before_execution": intent["response_mode"] != "implementation_handoff", "founder_approval_required": not bool(intent.get("founder_already_approved")), "company_intelligence_required": False},
            next_step=str(intent["next_step"]),
            clarification=clarification,
        )
    context = _board_room_context(reasoning_result)
    agenda = payload.get("agenda") or build_board_room_state()["default_agenda"]
    analysis = analyze_conversation({"message": message})
    intelligence = analysis.get("conversation_intelligence", {})
    normalized_message = str(intelligence.get("normalized_request") or message)
    guidance = ExecutiveReasoningEngine.build_ai_guidance(reasoning_result)
    ai_result = invoke_ai({"system": _board_room_system_prompt(), "prompt": _board_room_prompt(message=normalized_message, agenda=agenda, context=context, guidance=guidance), "provider": payload.get("provider"), "model": payload.get("model")})
    output_text = str(ai_result.get("output_text") or "").strip()
    deliberation = (
        run_board_room_deliberation(message=normalized_message)
        if _decision_ready_mission_requested(normalized_message)
        else None
    )
    action_metadata = _executive_action_metadata(reasoning_result, normalized_message, deliberation=deliberation)
    return present_founder_chat(
        status="board-room-response-ready" if ai_result.get("status") == "completed" else f"board-room-{ai_result.get('status', 'unknown')}",
        meeting_id=meeting_id,
        board_room_response=_founder_safe_response(
            output_text,
            reasoning_result["founder_response"],
            str(reasoning_result["reasoning"].get("presentation_mode") or "prioritization"),
        ),
        conversation_intelligence=intelligence,
        action_metadata=action_metadata,
        governance={"execution_allowed": False, "proposal_required_before_execution": True, "founder_approval_required": True, "company_intelligence_required": True},
        next_step=str(intelligence.get("recommended_next_action") or "Review the Board Room response. Generate a workflow only when you want to convert the discussion into an approval-gated workflow."),
    )


def chat_with_operating_console(payload: dict[str, Any]) -> dict[str, Any]:
    return board_room_chat(payload)


def _board_room_message_candidate(message: str) -> str:
    candidate = message.strip()
    if "Latest Founder message:" in candidate:
        candidate = candidate.rsplit("Latest Founder message:", 1)[-1]
    candidate = candidate.split("Persistent executive memory", 1)[0].strip()
    return candidate


def _classify_board_room_intent(
    message: str,
    *,
    pending_approval: Optional[dict[str, Any]] = None,
    conversation_history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    candidate = _board_room_message_candidate(message)
    normalized = " ".join(candidate.lower().replace("!", " ").replace("?", " ").replace(".", " ").replace(",", " ").split())
    words = normalized.split()
    tokens = set(words)
    casual_terms = {"hello", "hi", "hey", "yo", "morning", "evening", "thanks", "thank", "ok", "okay", "yes", "no", "nice", "cool", "great", "done", "test", "testing", "mission", "control"}
    if tokens and tokens <= casual_terms:
        return {"response_mode": "casual", "intent": "casual", "label": "Casual conversation", "message": candidate, "next_step": "No action required."}
    decomposition = RequestDecomposer().decompose(candidate)
    if _decision_ready_mission_requested(candidate):
        metadata = build_decision_ready_mission_actions(candidate)
        effort = estimate_effort(candidate, "engineering_execution")
        metadata.update({"effort_band": effort["band"], "estimated_effort": effort["estimate"]})
        return {
            "response_mode": "mission_preparation",
            "intent": "mission_creation",
            "label": "Decision-ready mission",
            "message": candidate,
            "next_step": metadata["recommended_action"],
            "founder_already_approved": False,
            "action_metadata": metadata,
            "request_decomposition": decomposition,
        }
    mode = ConversationModeClassifier.classify(
        candidate,
        decomposition,
        pending_approval=pending_approval,
        conversation_history=conversation_history,
    )
    if mode.mode == "mission_approval":
        return {
            "response_mode": "mission_approval",
            "intent": "mission_approval",
            "label": "Mission approval",
            "message": candidate,
            "next_step": "Launch the approved durable mission.",
            "request_decomposition": decomposition,
        }
    if decomposition.get("intent_type") == "informational_capability_query":
        return {
            "response_mode": "informational_capability_query",
            "intent": "informational_capability_query",
            "label": "Capability information",
            "message": candidate,
            "next_step": "No action is required.",
            "request_decomposition": decomposition,
        }
    if mode.mode == "direct_answer" and decomposition.get("dominant_goal") == "clarify":
        return {
            "response_mode": "clarify",
            "intent": "clarify",
            "label": "Clarification needed",
            "message": candidate,
            "next_step": "Clarify the desired outcome.",
            "request_decomposition": decomposition,
        }
    if mode.mode in CONVERSATIONAL_MODES:
        return {
            "response_mode": mode.mode,
            "intent": mode.mode,
            "label": mode.mode.replace("_", " ").title(),
            "message": candidate,
            "next_step": "Continue the conversation.",
            "request_decomposition": decomposition,
        }
    requested_action = str(decomposition["requested_action"])
    dominant_goal = str(decomposition.get("dominant_goal") or "")
    if dominant_goal == "clarify":
        return {
            "response_mode": "clarify",
            "intent": "clarify",
            "label": "Clarification needed",
            "message": candidate,
            "next_step": "Clarify the desired outcome.",
            "request_decomposition": decomposition,
        }
    if dominant_goal == "create_new_mission":
        metadata = (
            build_decision_ready_mission_actions(candidate)
            if _decision_ready_mission_requested(candidate)
            else _mission_preparation_actions(candidate)
        )
        return {
            "response_mode": "mission_preparation",
            "intent": "mission_creation",
            "label": "New mission preparation",
            "message": candidate,
            "next_step": metadata["recommended_action"],
            "founder_already_approved": False,
            "action_metadata": metadata,
            "request_decomposition": decomposition,
        }
    if requested_action in {"IMPLEMENT", "GOVERNED_ACTION"}:
        milestone = _detect_milestone(candidate)
        approved = _founder_already_approved(normalized)
        if requested_action == "GOVERNED_ACTION" and dominant_goal in {
            "merge_pull_request", "deploy_production", "rollback_production",
        }:
            approved = _exact_governed_approval_present(normalized, dominant_goal)
        handoff = _implementation_handoff(candidate, milestone, approved)
        if requested_action == "GOVERNED_ACTION":
            handoff["intent_type"] = "governed_action"
            handoff["recommended_action"] = "Review the governed action and use its existing approval gate."
        return {
            "response_mode": "implementation_handoff",
            "intent": "governed_action" if requested_action == "GOVERNED_ACTION" else "implementation_handoff",
            "label": "Governed action" if requested_action == "GOVERNED_ACTION" else "Implementation handoff",
            "message": candidate,
            "next_step": handoff["recommended_action"],
            "founder_already_approved": approved,
            "action_metadata": handoff,
            "request_decomposition": decomposition,
        }
    if requested_action in {"ANALYZE", "COMPARE", "DIAGNOSE", "RECOMMEND", "PLAN", "QUESTION"}:
        return {
            "response_mode": "structured",
            "intent": requested_action.lower(),
            "label": f"{requested_action.title()} request",
            "message": candidate,
            "next_step": "Review the analysis and decide whether a separate mission should be created.",
            "request_decomposition": decomposition,
        }
    if _is_governance_review(normalized):
        metadata = _mode_action_metadata("governance_review", "Review governance and choose approve, hold, or request changes.")
        return {"response_mode": "governance_review", "intent": "governance_review", "label": "Governance review", "message": candidate, "next_step": metadata["recommended_action"], "action_metadata": metadata}
    if _is_status_report(normalized):
        metadata = _mode_action_metadata("status_report", "Use the mission pipeline as the next status surface.")
        return {"response_mode": "status_report", "intent": "status_report", "label": "Status report", "message": candidate, "next_step": metadata["recommended_action"], "action_metadata": metadata}
    if _is_strategic_recommendation(normalized):
        metadata = _mode_action_metadata("strategic_recommendation", "Build the unified Mission Pipeline / Mission Orchestrator next.")
        return {"response_mode": "strategic_recommendation", "intent": "strategic_recommendation", "label": "Strategic recommendation", "message": candidate, "next_step": metadata["recommended_action"], "action_metadata": metadata}
    milestone = _detect_milestone(candidate)
    approved = _founder_already_approved(normalized) or "implement" in tokens
    implementation_terms = {"implement", "build", "fix", "generate", "execute", "proceed", "approved"}
    route_terms = {"pr", "github", "merge", "deploy", "deployment", "rollback"}
    direct_phrases = ("do not discuss", "implement now", "approved proceed", "open pr", "execute this", "generate files")
    if milestone or tokens & implementation_terms or any(phrase in normalized for phrase in direct_phrases) or (tokens & route_terms and len(words) <= 6):
        handoff = _implementation_handoff(candidate, milestone, approved)
        return {
            "response_mode": "implementation_handoff",
            "intent": "implementation_handoff",
            "label": "Implementation handoff",
            "message": candidate,
            "next_step": handoff["recommended_action"],
            "founder_already_approved": approved,
            "action_metadata": handoff,
        }
    structured_hits = tokens & BOARD_ROOM_STRUCTURED_INTENTS
    action_phrases = (
        "how do",
        "how should",
        "can you build",
        "create ",
        "fix ",
        "review ",
        "ship ",
        "set up",
        "what is the plan",
        "next step",
    )
    vague_phrases = {"help", "help me", "can you help", "can you help me", "what do you think"}
    if structured_hits or any(phrase in normalized for phrase in action_phrases):
        return {"response_mode": "structured", "intent": "board_room_work", "label": "Board Room work request", "message": candidate, "next_step": "Review the Board Room response and decide whether to create an approval-gated workflow."}
    if normalized in vague_phrases:
        return {"response_mode": "clarify", "intent": "unclear", "label": "Clarification needed", "message": candidate, "next_step": "Send one sentence about what you want the Board Room to help with."}
    if not normalized:
        return {"response_mode": "clarify", "intent": "unclear", "label": "Clarification needed", "message": candidate, "next_step": "Send one sentence about what you want the Board Room to help with."}
    if tokens & casual_terms and len(words) <= 5:
        return {"response_mode": "casual", "intent": "casual", "label": "Casual conversation", "message": candidate, "next_step": "No action required."}
    if len(normalized) <= 2:
        return {"response_mode": "clarify", "intent": "unclear", "label": "Clarification needed", "message": candidate, "next_step": "Send one sentence about what you want the Board Room to help with."}
    if len(words) <= 2:
        return {"response_mode": "clarify", "intent": "unclear", "label": "Clarification needed", "message": candidate, "next_step": "Send one sentence about what you want the Board Room to help with."}
    if len(words) <= 5 and "?" not in candidate:
        return {"response_mode": "clarify", "intent": "unclear", "label": "Clarification needed", "message": candidate, "next_step": "Send one sentence about what you want the Board Room to help with."}
    return {"response_mode": "structured", "intent": "board_room_work", "label": "Board Room work request", "message": candidate, "next_step": "Review the Board Room response and decide whether to create an approval-gated workflow."}


def _detect_milestone(text: str) -> str | None:
    match = re.search(r"\b([A-Z]{2,}(?:-[A-Z0-9]+)+-\d+)\b", text.upper())
    return match.group(1) if match else None


def _founder_already_approved(normalized: str) -> bool:
    return any(phrase in normalized for phrase in ("do not discuss", "implement now", "approved", "proceed", "execute"))


def _exact_governed_approval_present(normalized: str, dominant_goal: str) -> bool:
    phrases = {
        "execute_repository_change": "i approve github execution",
        "merge_pull_request": "i approve pr merge",
        "deploy_production": "i approve cloud run deployment",
        "rollback_production": "i approve cloud run rollback",
    }
    return phrases.get(dominant_goal) in normalized


def _is_strategic_recommendation(normalized: str) -> bool:
    phrases = (
        "biggest remaining gap",
        "what should we build next",
        "what would you not build next",
        "critique mission control",
        "one coherent product",
        "make this feel like one coherent product",
        "before ai software factory becomes an autonomous software company",
        "next biggest gap",
        "highest impact next",
    )
    return any(phrase in normalized for phrase in phrases)


def _is_status_report(normalized: str) -> bool:
    phrases = ("current status", "where are we", "where are we now", "capability matrix", "progress", "status report")
    return any(phrase in normalized for phrase in phrases)


def _is_governance_review(normalized: str) -> bool:
    phrases = ("deployment review", "approval review", "risk review", "governance review", "production movement review")
    return any(phrase in normalized for phrase in phrases)


def _mode_action_metadata(mode: str, recommended_action: str) -> dict[str, Any]:
    strategic_mission_actions = build_pending_mission_actions(
        "Implement MC-PIPELINE-01: unified Mission Pipeline / Mission Orchestrator."
    )
    buttons_by_mode = {
        "strategic_recommendation": [
            {"label": "Build Recommended Next", "action_type": "copy", "target": "clipboard", "payload": "Implement MC-PIPELINE-01: unified Mission Pipeline / Mission Orchestrator."},
            {"label": "Compare Options", "action_type": "note", "target": "addInlineNote", "payload": {"text": "Compare the Mission Pipeline against other possible next investments."}},
            *strategic_mission_actions["action_buttons"],
            {"label": "Copy Recommendation", "action_type": "copy", "target": "clipboard", "payload": "Recommendation: build the unified Mission Pipeline / Mission Orchestrator next."},
        ],
        "status_report": [
            {"label": "Refresh Status", "action_type": "post", "target": "/mission-control/verification/run", "payload": {}},
            {"label": "Open Mission Pipeline", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Copy Status", "action_type": "copy", "target": "clipboard", "payload": "Status: deploy, verification, rollback, GitHub execution, PR lifecycle, merge, and action routing foundations exist. The remaining gap is a unified mission pipeline."},
        ],
        "governance_review": [
            {"label": "Approve", "action_type": "note", "target": "addInlineNote", "payload": {"text": "Approval noted. Use the relevant approved execution panel for any live action."}},
            {"label": "Hold", "action_type": "note", "target": "addInlineNote", "payload": {"text": "Governance review held."}},
            {"label": "Request Changes", "action_type": "note", "target": "addInlineNote", "payload": {"text": "Requested changes before approval."}},
            {"label": "Copy Approval Payload", "action_type": "copy", "target": "clipboard", "payload": "Founder approval payload: approved / hold / request changes. Live execution still requires the exact module approval phrase."},
        ],
    }
    return {"intent_type": mode, "recommended_action": recommended_action, "action_buttons": buttons_by_mode.get(mode, [])}


def _implementation_handoff(founder_request: str, milestone: str | None, approved: bool, *, provider: Any = None, model: Any = None) -> dict[str, Any]:
    milestone = milestone or "implementation-request"
    if milestone == "MC-PIPELINE-01":
        branch = "mc-pipeline-01-unified-mission-pipeline"
        files = [
            "app/platform/pipeline/__init__.py",
            "app/platform/pipeline/mission_pipeline.py",
            "app/platform/server.py",
            "app/platform/ui/dashboard_browser_script.py",
            "app/platform/ui/founder_dashboard_stable.py only if needed",
        ]
        validation = [
            "python3 -m compileall app/platform",
            "python3 -m app.platform.ui.login_module_boundary_check",
            "python3 -m app.platform.ui.ui_module_size_check",
            "Dashboard render check",
            "node --check generated dashboard JS",
        ]
    else:
        branch = "mc-" + re.sub(r"[^a-z0-9]+", "-", milestone.lower()).strip("-")
        files = ["Determine exact files from repository inspection before editing."]
        validation = ["python3 -m compileall app/platform", "Run focused checks for touched modules."]
    handoff = "\n".join([
        f"Mission: {milestone}",
        f"Founder request: {founder_request}",
        f"Branch: {branch}",
        "Route: Engineering Worker implementation handoff, then GitHub Execution preview if file changes are approved.",
        "Expected files:",
        *[f"- {path}" for path in files],
        "Validation:",
        *[f"- {cmd}" for cmd in validation],
        "Governance: no merge, no deploy, no rollback, no traffic shift.",
    ])
    buttons = _contextual_action_buttons(founder_request, approved, provider=provider, model=model)
    effort = estimate_effort(founder_request, "engineering_execution")
    return {
        "intent_type": "implementation_handoff",
        "milestone": milestone,
        "recommended_action": "Create execution mission and hand this directly to Engineering Worker.",
        "handoff_prompt": handoff,
        "founder_approval_required": not approved,
        "effort_band": effort["band"],
        "estimated_effort": effort["estimate"],
        "action_buttons": buttons,
    }


def _ui_ux_proposal_response(payload: dict[str, Any], message: str, meeting_id: str) -> dict[str, Any]:
    conversation_id = str(payload.get("conversation_id") or meeting_id)
    proposal = propose_ui_change({
        "token": payload.get("token"),
        "change_request": message,
        "conversation_id": conversation_id,
    })
    if proposal.get("status") != "proposed":
        text = {
            "target_not_resolved": proposal.get("error") or "I could not tell which UI element this refers to.",
            "target_not_found": proposal.get("error") or "That target file does not exist.",
            "provider_error": "I could not reach the AI provider to draft this change: %s" % proposal.get("error"),
            "draft_parse_error": "The draft came back in an unusable format. Please try rephrasing the request.",
            "draft_incomplete": "The draft was missing required details. Please try rephrasing the request.",
            "anchor_not_found": "I could not find an exact anchor point for this change in the file. Try describing the element more precisely.",
            "anchor_ambiguous": "The change I drafted was ambiguous about where it applies. Try describing the element more precisely.",
            "unauthorised": "Please log in again before requesting a UI/UX change.",
        }.get(proposal.get("status"), proposal.get("error") or "I could not prepare a proposal for that request.")
        return present_founder_chat(
            status="board-room-response-ready",
            meeting_id=meeting_id,
            board_room_response=text,
            conversation_intelligence={
                "mode": "Ui Ux Proposal",
                "normalized_request": message,
                "decisions": [], "actions": [], "mission_proposals": [], "knowledge": [],
                "recommended_next_action": "Rephrase the request or specify target_file explicitly.",
                "intent_type": "ui_ux_proposal_failed",
                "decision_experience": None,
            },
            action_metadata={"intent_type": "ui_ux_proposal_failed", "recommended_action": "", "action_buttons": []},
            governance={"execution_allowed": False, "proposal_required_before_execution": True, "founder_approval_required": False, "company_intelligence_required": False},
            next_step="Rephrase the request or specify target_file explicitly.",
        )

    proposal_id = str(proposal["proposal_id"])
    response_text = (
        "Here is what I'm proposing to change in `%s`:\n\n%s\n\nI've rendered a preview of the change below. "
        "Approve to open a real pull request (still gated by the usual merge/deploy approval), tell me what to "
        "change, or reject." % (proposal["target_file"], proposal["sow_markdown"])
    )
    action_metadata = {
        "intent_type": "ui_ux_proposal",
        "recommended_action": "Review the proposed UI/UX change and approve, request changes, or reject.",
        "action_buttons": [
            {
                "label": "Approve",
                "action_type": "function",
                "target": "approveUiUxChange",
                "payload": {"proposal_id": proposal_id},
            },
            {
                "label": "Request Changes",
                "action_type": "function",
                "target": "requestUiUxIteration",
                "payload": {"proposal_id": proposal_id},
            },
            {
                "label": "Reject",
                "action_type": "post",
                "target": "/mission-control/ui-ux-agent/reject",
                "payload": {"proposal_id": proposal_id},
            },
        ],
        "ui_ux_proposal": {
            "proposal_id": proposal_id,
            "target_file": proposal["target_file"],
            "screenshot_base64": proposal.get("screenshot_base64"),
            "preview_status": proposal.get("preview_status"),
        },
    }
    return present_founder_chat(
        status="board-room-response-ready",
        meeting_id=meeting_id,
        board_room_response=response_text,
        conversation_intelligence={
            "mode": "Ui Ux Proposal",
            "normalized_request": message,
            "decisions": [], "actions": [], "mission_proposals": [], "knowledge": [],
            "recommended_next_action": action_metadata["recommended_action"],
            "intent_type": "ui_ux_proposal",
            "decision_experience": None,
        },
        action_metadata=action_metadata,
        governance={
            "execution_allowed": False,
            "proposal_required_before_execution": True,
            "founder_approval_required": True,
            "company_intelligence_required": False,
        },
        next_step=action_metadata["recommended_action"],
    )


def _contextual_action_buttons(founder_request: str, approved: bool, *, provider: Any = None, model: Any = None) -> list[dict[str, Any]]:
    text = founder_request.lower()
    if "rollback" in text:
        return [
            {"label": "Preview Rollback", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Open Rollback Panel", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Save Mission", "action_type": "function", "target": "saveCurrentSession", "payload": {}},
        ]
    if "deploy" in text or "deployment" in text or "cloud run" in text:
        return [
            {"label": "Preview Deployment", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Open Deployment Panel", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Run Verification", "action_type": "show_section", "target": "executions", "payload": {}},
        ]
    if "merge" in text:
        return [
            {"label": "Preview Merge", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Open Merge Panel", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Copy Merge Approval Phrase", "action_type": "copy", "target": "clipboard", "payload": "I APPROVE PR MERGE"},
        ]
    if re.search(r"\bpr\b", text) or "pull request" in text or "github" in text:
        return [
            {"label": "Check PR Status", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Preview GitHub Execution", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Execute with Approval", "action_type": "show_section", "target": "executions", "payload": {}},
            {"label": "Open PR Lifecycle", "action_type": "show_section", "target": "executions", "payload": {}},
        ]
    governed = (
        build_pending_mission_actions(founder_request, provider=provider, model=model)
        if approved
        else build_decision_ready_mission_actions(founder_request, provider=provider, model=model)
    )
    governed_buttons = []
    for button in governed["action_buttons"]:
        if button["label"] == "Approve Mission" and approved:
            launch = dict(button)
            launch.update({"label": "Create Execution Mission", "expects_durable_run": True})
            governed_buttons.append(launch)
        else:
            governed_buttons.append(button)
    return governed_buttons


def _adaptive_board_response(intent: dict[str, Any]) -> str:
    mode = str(intent.get("response_mode") or "")
    if mode == "implementation_handoff":
        return _implementation_handoff_response(intent)
    if mode == "strategic_recommendation":
        return _strategic_recommendation_response()
    if mode == "status_report":
        return _status_report_response()
    if mode == "governance_review":
        return _governance_review_response()
    return _conversational_board_response(intent)


def _implementation_handoff_response(intent: dict[str, Any]) -> str:
    metadata = intent.get("action_metadata") if isinstance(intent.get("action_metadata"), dict) else {}
    milestone = metadata.get("milestone") or "implementation request"
    approval_line = "Founder approval is already present in your command, so I will not ask again." if intent.get("founder_already_approved") else "Founder approval is required before live execution."
    return "\n".join([
        f"Understood. Routing {milestone} as an implementation handoff.",
        "",
        approval_line,
        "",
        metadata.get("handoff_prompt") or str(intent.get("message") or ""),
    ])


def _minimal_action_metadata(intent: dict[str, Any]) -> dict[str, Any]:
    if intent.get("intent") == "casual" or intent.get("intent") == "informational_capability_query" or intent.get("response_mode") in CONVERSATIONAL_MODES:
        return {"intent_type": str(intent.get("intent") or "conversation"), "recommended_action": "No action required.", "action_buttons": []}
    return {"intent_type": str(intent.get("intent") or "discussion"), "recommended_action": str(intent.get("next_step") or "Continue discussion."), "action_buttons": [{"label": "Save Session", "action_type": "function", "target": "saveCurrentSession", "payload": {}}]}


def _mission_preparation_actions(
    founder_request: str,
    *,
    provider: Any = None,
    model: Any = None,
) -> dict[str, Any]:
    return build_pending_mission_actions(founder_request, provider=provider, model=model)


def _executive_action_metadata(
    reasoning_result: dict[str, Any],
    founder_request: str,
    *,
    deliberation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasoning = reasoning_result.get("reasoning") or {}
    recommendation = reasoning.get("recommendation") or {}
    governance = reasoning.get("governance") or {}
    decomposition = reasoning.get("request_decomposition") or {}
    requested_action = str(decomposition.get("requested_action") or "")
    dominant_goal = str(decomposition.get("dominant_goal") or "")
    analytical_actions = {"ANALYZE", "COMPARE", "DIAGNOSE", "RECOMMEND", "PLAN", "QUESTION"}
    if _decision_ready_mission_requested(founder_request):
        metadata = build_decision_ready_mission_actions(founder_request)
        consensus = (deliberation or {}).get("consensus") or {}
        effort = estimate_effort(founder_request, "engineering_execution")
        metadata.update({
            "effort_band": consensus.get("effort_band") or effort["band"],
            "estimated_effort": consensus.get("estimated_effort") or effort["estimate"],
        })
        return metadata
    if dominant_goal == "continue_existing_mission":
        buttons = [
            {
                "label": "Open Mission Pipeline",
                "action_type": "show_section",
                "target": "executions",
                "payload": {},
            },
            {
                "label": "Save Mission",
                "action_type": "function",
                "target": "saveCurrentSession",
                "payload": {},
            },
        ]
    elif requested_action in analytical_actions:
        buttons = [
            {
                "label": "Save Analysis",
                "action_type": "function",
                "target": "saveCurrentSession",
                "payload": {},
            },
            {
                "label": "Explore Recommended Milestone",
                "action_type": "copy",
                "target": "clipboard",
                "payload": str(recommendation.get("action") or reasoning.get("next_action") or ""),
            },
        ]
    else:
        buttons = [
            *build_pending_mission_actions(founder_request)["action_buttons"],
            {
                "label": "Ask More Questions",
                "action_type": "note",
                "target": "addInlineNote",
                "payload": {"text": "What would you like the Board Room to examine more deeply?"},
            },
        ] if governance.get("required") else []
    action_intent = (
        dominant_goal
        if dominant_goal in {"create_new_mission", "continue_existing_mission"}
        else (requested_action.lower() if requested_action else str(reasoning.get("intent") or "executive discussion"))
    )
    return {
        "intent_type": action_intent,
        "recommended_action": str(recommendation.get("action") or reasoning.get("next_action") or "Review recommendation"),
        "reason": str(recommendation.get("why") or ""),
        "technical_details": reasoning_result.get("technical_details") or {},
        "action_buttons": buttons,
    }


def _decision_ready_mission_requested(founder_request: str) -> bool:
    normalized = " ".join(founder_request.lower().split())
    recommendation = bool(re.search(r"\b(?:recommend|recommendation|highest-impact|highest impact)\b", normalized))
    mission = bool(re.search(r"\b(?:mission|proposal|scope)\b", normalized))
    decision = bool(re.search(r"\b(?:approve|decision-ready|decision ready)\b", normalized))
    return recommendation and mission and decision


def _strategic_recommendation_response() -> str:
    return "\n".join([
        "The biggest remaining gap is the unified Mission Pipeline: one orchestrated path from founder intent to engineering plan, approved execution, PR, verification, deployment, and rollback readiness.",
        "",
        "Why: you now have strong individual modules, but autonomy needs a single operating loop that knows the current mission state, next allowed action, required approval, validation status, and handoff target.",
        "",
        "Recommended next move: build MC-PIPELINE-01 as the Mission Pipeline / Mission Orchestrator.",
        "",
        "- Make Board Room handoffs become tracked missions.",
        "- Connect Engineering Manager, GitHub Execution, PR Lifecycle, Merge, Deployment, Verification, and Rollback into one state machine.",
        "- Show one founder-facing mission timeline instead of separate tool panels.",
        "- Keep merge, deploy, rollback, and traffic movement approval-gated.",
    ])


def _status_report_response() -> str:
    return "\n".join([
        "Current status: Mission Control has the core governed execution modules online, but they are still more like connected tools than one autonomous software company loop.",
        "",
        "- Done: GitHub execution, PR lifecycle, approved merge, approved deployment, production verification, approved rollback, and Board Room action routing foundations.",
        "- Gap: unified mission state across planning, execution, PR, CI, deploy, verify, and rollback.",
        "- Next: MC-PIPELINE-01 should become the single mission timeline and orchestration layer.",
    ])


def _governance_review_response() -> str:
    return "\n".join([
        "Governance review ready.",
        "",
        "Founder Decision Required: approve, hold, or request changes before any live production or repository action.",
        "",
        "- No deployment, merge, rollback, or traffic movement should run from this discussion alone.",
        "- Use the specific approved execution panel for the live action and exact approval phrase.",
    ])


def _conversational_board_response(intent: dict[str, Any]) -> str:
    if intent["response_mode"] == "clarify":
        return "What would you like the Board Room to help with?"
    message = str(intent["message"]).strip().lower()
    if "test" in message:
        return "Test received. Board Room is online and ready."
    if message in {"thanks", "thank you"}:
        return "You are welcome. What should we tackle next?"
    if message in {"ok", "okay", "yes", "done", "nice", "cool", "great"}:
        return "Got it. I am ready for the next thing."
    return "Hi Toni. Board Room is ready. What would you like to work on?"


def run_console_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return {"status": "unauthorized", "authenticated": False, "message": "Please login to Mission Control before running workflows."}
    action = str(payload.get("action") or "create-proposal").strip().lower()
    if action == "generate-executable-change-set":
        change_set = generate_executable_change_set(payload)
        return {"company": "AI Software Factory", "product": "Founder Operating Console", "status": "change-set-ready" if change_set.get("change_set_status") == "change_set_ready" else "workflow-blocked", "authenticated": True, "role": authorized.get("role", "founder"), "action": action, "mission_id": change_set.get("mission_id"), "executable_change_set": change_set, "next_step": change_set.get("next_required_action") or change_set.get("blocked_reason")}
    if action in {"authorize-engineering-execution", "execute-engineering"}:
        workflow = execute_authorized_engineering_workflow(payload)
        return {
            "company": "AI Software Factory",
            "product": "Founder Operating Console",
            "status": "workflow-pr-created" if workflow.get("workflow_status") == "pull-request-created-and-observed" else "workflow-blocked",
            "authenticated": True,
            "role": authorized.get("role", "founder"),
            "action": action,
            "mission_id": workflow.get("mission_id"),
            "engineering_execution_workflow": workflow,
            "next_step": workflow.get("next_required_action"),
        }
    raw_request_text = str(payload.get("message") or payload.get("request") or payload.get("prompt") or "").strip()
    if not raw_request_text:
        return {"status": "invalid-request", "error": "message/request is required"}
    intelligence = analyze_conversation({"message": raw_request_text}).get("conversation_intelligence", {})
    request_text = str(intelligence.get("normalized_request") or raw_request_text)
    semantic = intelligence.get("semantic_model") if isinstance(intelligence.get("semantic_model"), dict) else {}
    intent_title = str(semantic.get("intent_title") or request_text[:80])
    mission_id = str(payload.get("mission_id") or _id("MISSION", _now(), {"request": request_text, "action": action}))
    intake = build_request_intake({"request": request_text, "mission_id": mission_id, "source": "board-room"})
    proposal = _roadmap_proposal_record(intelligence, mission_id, request_text) if intelligence.get("workflow_type") == "roadmap" else generate_proposal({"request": request_text, "mission_id": mission_id, "title": payload.get("title") or intent_title})
    result: dict[str, Any] = {"company": "AI Software Factory", "product": "Founder Operating Console", "milestone": "INT-01", "status": "workflow-created", "authenticated": True, "role": authorized.get("role", "founder"), "action": action, "mission_id": mission_id, "intake": intake, "proposal": proposal, "conversation_intelligence": intelligence, "company_intelligence": build_executive_intelligence_briefing(), "next_step": str(intelligence.get("recommended_next_action") or "Review the proposal in Mission Control and approve before execution.")}
    if action in {"approve", "approve-and-plan", "approve-and-start"}:
        approval = approve_proposal({"proposal_id": proposal.get("proposal", {}).get("proposal_id") or payload.get("proposal_id") or mission_id, "mission_id": mission_id, "originating_mission_id": payload.get("originating_mission_id"), "approved_by": authorized.get("email") or payload.get("approved_by") or "founder", "approval_notes": "Approved from Founder Operating Console."})
        result["approval"] = approval
        result["mission_id"] = _approved_mission_id(mission_id, approval)
        if intelligence.get("workflow_type") == "roadmap":
            result["status"] = "workflow-approved"
            result["next_step"] = "Select the first roadmap mission."
        else:
            launch = launch_approved_mission_workflow({"token": payload.get("token"), "approval": approval, "founder_request": request_text, "title": payload.get("title") or intent_title})
            result["approved_mission_workflow"] = launch
            result["status"] = "workflow-engineering-handoff-prepared" if launch.get("workflow_status") == "engineering-handoff-prepared" else "workflow-blocked"
            result["next_step"] = str(launch.get("next_required_action"))
    if action == "plan" and intelligence.get("workflow_type") != "roadmap":
        plan = plan_mission({"mission_id": result["mission_id"], "title": payload.get("title") or intent_title, "goal": request_text})
        result["mission_plan"] = plan
        result["status"] = "workflow-planned"
        result["next_step"] = "Start the mission when ready."
    if action == "start" and intelligence.get("workflow_type") != "roadmap":
        started = start_mission({"mission_id": result["mission_id"], "title": payload.get("title") or intent_title, "goal": request_text})
        result["mission_start"] = started
        result["status"] = "workflow-started"
        result["next_step"] = "Use repository intelligence, code generation, GitHub executor, and CI repair queues from the dashboard."
    result["founder_workflow"] = build_workflow_from_console_result(result, request_text)
    return result


def _approved_mission_id(provisional_mission_id: str, approval: dict[str, Any]) -> str:
    return str(approval.get("mission_id") or provisional_mission_id)


def _roadmap_proposal_record(intelligence: dict[str, Any], mission_id: str, request_text: str) -> dict[str, Any]:
    roadmap = intelligence.get("roadmap_proposal") if isinstance(intelligence.get("roadmap_proposal"), dict) else {}
    semantic = intelligence.get("semantic_model") if isinstance(intelligence.get("semantic_model"), dict) else {}
    return {
        "company": "AI Software Factory",
        "product": "Roadmap Proposal Generator",
        "status": "roadmap-generated-for-founder-review",
        "proposal_id": f"ROADMAP-{mission_id}",
        "proposal": {
            "proposal_id": f"ROADMAP-{mission_id}",
            "title": semantic.get("intent_title") or roadmap.get("title") or "Mission Control Engineering Roadmap",
            "status": "generated",
            "executive_summary": semantic.get("intent_summary") or "Prioritized mission roadmap generated from Board Room discussion. Approval authorizes planning only, not implementation.",
            "business_objective": request_text,
            "recommended_solution": "Review and approve the roadmap, then select a single mission for implementation planning.",
            "semantic_model": semantic,
            "roadmap": roadmap,
            "acceptance_criteria": ["Roadmap is visible for Founder review.", "No implementation begins from roadmap approval alone."],
        },
        "next_step": "Founder reviews roadmap and selects a mission for separate implementation approval.",
    }


def _board_room_context(reasoning_result: dict[str, Any]) -> dict[str, Any]:
    context = reasoning_result.get("context") if isinstance(reasoning_result.get("context"), dict) else {}
    sources = context.get("sources") if isinstance(context.get("sources"), dict) else {}
    executive = sources.get("executive_intelligence")
    return executive if isinstance(executive, dict) else {"status": "unknown", "unknown_reason": "Executive Intelligence context was unavailable."}


def _board_room_system_prompt() -> str:
    return "You are the AI Software Factory Chief of Staff. Lead with one clear recommendation, explain why in business language, give concise context, compare viable alternatives, state risk, and end with one next action. Use supplied company context as evidence and distinguish facts from assumptions. Never claim execution. Do not expose implementation mechanics unless the founder explicitly asks for them."


def _board_room_prompt(*, message: str, agenda: Any, context: dict[str, Any], guidance: str) -> str:
    return f"""
Founder message:
{message}

Board agenda:
{json.dumps(agenda, indent=2)}

Executive Intelligence snapshot:
{json.dumps(context, indent=2, sort_keys=True, default=str)}

Executive reasoning guidance:
{guidance}

Follow the presentation mode and decision evidence in the guidance.
Use only sections relevant to that mode and do not force a generic template.
""".strip()


def _fallback_board_response(ai_result: dict[str, Any]) -> str:
    return f"Board Room could not complete AI response. Status: {ai_result.get('status', 'unknown')}. Detail: {ai_result.get('error') or 'No AI output was returned.'}"


def _founder_safe_response(ai_output: str, fallback: str, presentation_mode: str) -> str:
    if not ai_output:
        return fallback
    if len(ai_output.split()) < 12:
        return fallback
    lowered = ai_output.lower()
    hidden_terms = (
        "compileall",
        "dto",
        "json payload",
        "api route",
        "branch name",
        "validation command",
        "status code",
        "execution-first routing",
        "jarvis must",
        "system instruction",
        "internal routing",
    )
    if any(term in lowered for term in hidden_terms):
        return fallback
    if re.search(r"\b\d{1,3}/100\b", ai_output):
        return fallback
    unsafe_claims = (
        "i deployed",
        "i merged",
        "i pushed",
        "execution completed",
        "production traffic shifted",
    )
    if any(claim in lowered for claim in unsafe_claims):
        return fallback
    return ai_output


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
