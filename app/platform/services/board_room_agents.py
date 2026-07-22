from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.executive_context_service import format_context_block


@dataclass(frozen=True)
class BoardRoomAgent:
    key: str
    title: str
    mandate: str
    lens: str


BOARD_ROOM_AGENTS: tuple[BoardRoomAgent, ...] = (
    BoardRoomAgent("ceo", "CEO", "Decide whether this advances the company vision, customer value, and execution focus.", "vision, sequencing, founder leverage, company-building clarity"),
    BoardRoomAgent("cto", "CTO", "Assess technical architecture, implementation risk, maintainability, and deployment safety.", "architecture, production stability, reviewable PRs, technical debt"),
    BoardRoomAgent("cfo", "CFO", "Assess cost, ROI, funding impact, runway, and whether the work compounds enterprise value.", "ROI, burn, pricing leverage, investor-grade discipline"),
    BoardRoomAgent("cmo", "CMO", "Assess market positioning, founder story, user clarity, and GTM implications.", "positioning, adoption, messaging, customer pull"),
    BoardRoomAgent("coo", "COO", "Assess operational feasibility, sequencing, handoffs, and process reliability.", "execution systems, workflow hygiene, operational simplicity"),
    BoardRoomAgent("cso", "Chief Strategy Officer", "Assess competitive advantage, wedge, market timing, and strategic narrative.", "moat, sequencing, strategic trade-offs, category creation"),
    BoardRoomAgent("counsel", "General Counsel", "Assess governance, approval boundaries, privacy, security, and production risk.", "governance, protected auth boundary, data handling, compliance posture"),
    BoardRoomAgent("vc_partner", "VC Partner", "Assess whether this makes the company more fundable and more obviously venture-scale.", "venture narrative, speed, defensibility, market size, proof points"),
    BoardRoomAgent("devil_advocate", "Devil's Advocate", "Challenge assumptions, identify failure modes, and expose hidden complexity.", "risks, contradictions, premature scale, wasted motion"),
)


def _trim(text: str, limit: int = 900) -> str:
    return (text or "").strip()[:limit]


def _classify_intent(message: str) -> str:
    lowered = message.lower()
    if re.search(r"\b(?:implement|build|fix|create|endpoint|tests?|pr|deploy)\b|\bpull request\b|\bprepare\b[^.]{0,80}\bmission\b", lowered):
        return "engineering_execution"
    if any(word in lowered for word in ("fundraising", "vc", "investor", "pitch")):
        return "fundraising_strategy"
    if any(word in lowered for word in ("architecture", "technical debt", "repository")):
        return "architecture_review"
    if any(word in lowered for word in ("pricing", "revenue", "market", "gtm")):
        return "go_to_market"
    return "executive_strategy"


def estimate_effort(message: str, intent: str) -> Dict[str, str]:
    lowered = message.lower()
    tiny_markers = ("/health", "health endpoint", "unit test", "single endpoint", "one endpoint", "small copy change", "rename label")
    small_markers = ("add endpoint", "add test", "simple", "focused improvement", "single page", "one page")
    if any(marker in lowered for marker in tiny_markers):
        return {"band": "Tiny", "estimate": "5–15 minutes"}
    if any(marker in lowered for marker in small_markers):
        return {"band": "Small", "estimate": "15–30 minutes"}
    if intent == "engineering_execution":
        return {"band": "Medium", "estimate": "30–90 minutes"}
    return {"band": "Small", "estimate": "15–30 minutes"}


def _agent_position(agent: BoardRoomAgent, message: str, context_block: str) -> Dict[str, str]:
    intent = _classify_intent(message)
    context_hint = "uses stored company context" if context_block and "No persistent" not in context_block else "no durable context yet"
    focus = agent.lens.split(",")[0].strip()
    recommendation = "proceed with a small, reversible, founder-approved PR" if intent == "engineering_execution" else "clarify the decision and preserve optionality"
    risk = "scope creep" if agent.key in {"cto", "coo", "devil_advocate"} else "weak signal-to-noise if the decision is not tied to company value"
    if agent.key == "counsel":
        recommendation = "proceed only if auth, login, session handling, and deployment controls remain untouched unless explicitly scoped"
        risk = "accidentally expanding the protected production-stability boundary"
    elif agent.key == "vc_partner":
        recommendation = "prioritize work that makes the product feel less like a wrapper and more like an operating system"
        risk = "building internal polish without increasing investor-obvious differentiation"
    elif agent.key == "devil_advocate":
        recommendation = "force the mission into the smallest independently reviewable increment"
        risk = "claiming multi-agent behavior without observable independent roles, memory, and synthesis"
    return {
        "agent": agent.key,
        "title": agent.title,
        "mandate": agent.mandate,
        "position": f"From the {focus} lens, this request is a {intent.replace('_', ' ')} decision and {context_hint}.",
        "recommendation": recommendation,
        "risk": risk,
    }


def _evidence(context_block: str, scope: str) -> List[Dict[str, str]]:
    if not context_block or "No persistent" in context_block:
        return [{"source": "executive_context", "status": "unavailable", "summary": "No persistent executive context was available for this deliberation."}]
    return [
        {"source": "executive_context", "status": "available", "summary": _trim(context_block, 420)},
        {"source": "scope", "status": "available", "summary": f"Deliberation used the existing {scope} scope."},
    ]


def _governance(intent: str) -> Dict[str, Any]:
    execution_intent = intent == "engineering_execution"
    return {
        "founder_approval_required": execution_intent,
        "execution_allowed": False,
        "workflow_authority": "existing_founder_workflow_engine",
        "mission_authority": "existing_mission_pipeline",
        "decision_authority": "existing_executive_decision_center",
        "protected_boundaries": ["authentication", "deployment", "production mutation"],
    }


def _guided_action(intent: str, message: str) -> Dict[str, Any]:
    effort = estimate_effort(message, intent)
    if intent == "engineering_execution":
        return {
            "key": "approve_mission",
            "label": "Approve Mission",
            "requires_workflow": True,
            "workflow_type": "implementation",
            "target_stage": "founder_approval",
            "effort_band": effort["band"],
            "estimated_effort": effort["estimate"],
        }
    if intent == "architecture_review":
        return {
            "key": "generate_architecture_roadmap",
            "label": "Generate Architecture Roadmap",
            "requires_workflow": True,
            "workflow_type": "roadmap",
            "target_stage": "roadmap_proposal",
            "effort_band": effort["band"],
            "estimated_effort": effort["estimate"],
        }
    return {
        "key": "continue_discussion",
        "label": "Continue Executive Discussion",
        "requires_workflow": False,
        "workflow_type": None,
        "target_stage": None,
        "effort_band": effort["band"],
        "estimated_effort": effort["estimate"],
    }


def _action_buttons(intent: str, message: str) -> List[Dict[str, Any]]:
    if intent != "engineering_execution":
        return []
    return [
        {
            "label": "Approve Mission",
            "action_type": "post",
            "target": "/mission-control/operating-console/action",
            "expects_durable_run": True,
            "payload": {"action": "approve_mission", "message": message},
        },
        {
            "label": "Edit Scope",
            "action_type": "function",
            "target": "editRecommendedScope",
            "payload": {"message": message},
        },
        {
            "label": "Reject",
            "action_type": "post_secondary",
            "target": "/mission-control/operating-console/action",
            "payload": {"action": "reject_mission", "message": message},
        },
    ]


def run_board_room_deliberation(*, message: str, db: Optional[Session] = None, scope: str = "mission_control") -> Dict[str, Any]:
    context_block = format_context_block(db=db, scope=scope) if db is not None else "No persistent executive context has been captured yet."
    intent = _classify_intent(message)
    effort = estimate_effort(message, intent)
    agent_positions = [_agent_position(agent, message, context_block) for agent in BOARD_ROOM_AGENTS]
    risks = [item["risk"] for item in agent_positions[:4]]
    contributors = [{"agent": item["agent"], "title": item["title"], "mandate": item["mandate"], "contribution": item["position"]} for item in agent_positions]
    consensus = {
        "decision": "Proceed only as a small founder-approved mission with explicit scope and rollback path.",
        "why": "The Board Room agents agree that the next step should increase product differentiation while preserving production stability.",
        "risks": risks,
        "next_action": "Approve the focused mission, edit its scope, or reject it.",
        "confidence": "high" if context_block and "No persistent" not in context_block else "medium",
        "effort_band": effort["band"],
        "estimated_effort": effort["estimate"],
    }
    return {
        "mode": "true_multi_agent_board_room",
        "version": "executive-board-room-v2",
        "scope": scope,
        "intent": intent,
        "context_available": "No persistent" not in context_block,
        "context_excerpt": _trim(context_block, 1200),
        "contributors": contributors,
        "agents": agent_positions,
        "evidence": _evidence(context_block, scope),
        "consensus": consensus,
        "governance": _governance(intent),
        "guided_action": _guided_action(intent, message),
        "action_buttons": _action_buttons(intent, message),
        "state_authorities": {
            "conversation": "existing_operating_console",
            "context": "existing_executive_context_service",
            "workflow": "existing_founder_workflow_engine",
            "mission": "existing_mission_pipeline",
        },
        "creates_parallel_capability": False,
    }


def format_deliberation_markdown(deliberation: Dict[str, Any]) -> str:
    lines: List[str] = ["## Executive Board Room v2", ""]
    evidence = deliberation.get("evidence") or []
    if evidence:
        lines.extend(["### Evidence", ""])
        for item in evidence:
            lines.append(f"- **{item.get('source', 'source')}** ({item.get('status', 'unknown')}): {item.get('summary', '')}")
        lines.append("")
    lines.extend(["### Executive Contributors", ""])
    for agent in deliberation.get("agents", []):
        lines.extend([f"#### {agent['title']}", f"**Position:** {agent['position']}", f"**Recommendation:** {agent['recommendation']}", f"**Risk:** {agent['risk']}", ""])
    consensus = deliberation.get("consensus", {})
    lines.extend([
        "## Synthesized Decision",
        f"**Decision:** {consensus.get('decision', '')}",
        f"**Why:** {consensus.get('why', '')}",
        f"**Confidence:** {consensus.get('confidence', 'unknown')}",
        f"**Estimated effort:** {consensus.get('effort_band', 'Unknown')} · {consensus.get('estimated_effort', 'Unknown')}",
        "",
        "### Risks",
    ])
    lines.extend([f"- {risk}" for risk in (consensus.get("risks") or [])] or ["- No risks were surfaced."])
    governance = deliberation.get("governance") or {}
    lines.extend([
        "",
        "### Governance",
        f"- Founder approval required: {bool(governance.get('founder_approval_required'))}",
        f"- Execution allowed in deliberation: {bool(governance.get('execution_allowed'))}",
        f"- Workflow authority: {governance.get('workflow_authority', '')}",
        f"- Mission authority: {governance.get('mission_authority', '')}",
        "",
        "### Guided Next Action",
    ])
    action = deliberation.get("guided_action") or {}
    lines.extend([
        f"**Action:** {action.get('label', consensus.get('next_action', ''))}",
        f"**Requires workflow:** {bool(action.get('requires_workflow'))}",
        f"**Effort:** {action.get('effort_band', 'Unknown')} · {action.get('estimated_effort', 'Unknown')}",
    ])
    return "\n".join(lines)
