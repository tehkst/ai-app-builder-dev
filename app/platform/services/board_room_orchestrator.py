from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.board_room_agents import BOARD_ROOM_AGENTS, BoardRoomAgent, run_board_room_deliberation
from app.platform.services.executive_context_service import format_context_block


AGENT_PRIORITY_BY_INTENT: dict[str, list[str]] = {
    "engineering_execution": ["cto", "counsel", "coo", "devil_advocate", "ceo", "vc_partner"],
    "architecture_review": ["cto", "devil_advocate", "coo", "counsel", "ceo"],
    "fundraising_strategy": ["vc_partner", "cso", "ceo", "cfo", "cmo", "devil_advocate"],
    "go_to_market": ["cmo", "cso", "cfo", "ceo", "vc_partner", "devil_advocate"],
    "executive_strategy": ["ceo", "cso", "cfo", "coo", "devil_advocate"],
}

STAGE_LIBRARY: dict[str, list[str]] = {
    "engineering_execution": ["scope_guard", "architecture_review", "risk_review", "execution_plan", "consensus"],
    "architecture_review": ["context_review", "architecture_review", "dissent_review", "mission_selection", "consensus"],
    "fundraising_strategy": ["market_narrative", "investor_lens", "financial_lens", "dissent_review", "consensus"],
    "go_to_market": ["customer_lens", "pricing_lens", "positioning_lens", "dissent_review", "consensus"],
    "executive_strategy": ["context_review", "strategic_options", "risk_review", "decision", "consensus"],
}


def classify_intent(message: str) -> str:
    lowered = message.lower()
    if any(word in lowered for word in ("implement", "build", "fix", "pr", "deploy")):
        return "engineering_execution"
    if any(word in lowered for word in ("fundraising", "vc", "investor", "pitch")):
        return "fundraising_strategy"
    if any(word in lowered for word in ("architecture", "technical debt", "repository")):
        return "architecture_review"
    if any(word in lowered for word in ("pricing", "revenue", "market", "gtm")):
        return "go_to_market"
    return "executive_strategy"


def trim_text(text: str, limit: int = 900) -> str:
    return (text or "").strip()[:limit]


def agents_by_key() -> dict[str, BoardRoomAgent]:
    return {agent.key: agent for agent in BOARD_ROOM_AGENTS}


def select_agents(message: str, max_agents: int = 6) -> list[BoardRoomAgent]:
    intent = classify_intent(message)
    lookup = agents_by_key()
    selected: list[BoardRoomAgent] = []
    for key in AGENT_PRIORITY_BY_INTENT.get(intent, AGENT_PRIORITY_BY_INTENT["executive_strategy"]):
        agent = lookup.get(key)
        if agent is not None:
            selected.append(agent)
    return selected[:max_agents]


def stage_payload(stage: str, agents: list[BoardRoomAgent], intent: str) -> dict[str, Any]:
    participants = [agent.title for agent in agents[:3]]
    if stage in {"dissent_review", "risk_review"}:
        participants = [agent.title for agent in agents if agent.key in {"devil_advocate", "counsel", "cto", "coo"}] or participants
    if stage == "consensus":
        participants = [agent.title for agent in agents]
    return {"stage": stage, "intent": intent, "participants": participants, "status": "planned"}


def confidence_score(intent: str, selected_agents: list[BoardRoomAgent], context_available: bool, risk_count: int) -> float:
    score = 0.58 + min(len(selected_agents), 6) * 0.035
    if context_available:
        score += 0.12
    if intent in {"engineering_execution", "architecture_review"}:
        score += 0.04
    score -= min(risk_count, 3) * 0.035
    return round(max(0.35, min(score, 0.92)), 2)


def extract_risk_reviews(deliberation: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for agent in deliberation.get("agents", []):
        if agent.get("agent") in {"devil_advocate", "counsel", "cto", "coo"}:
            items.append({"agent": agent.get("title", "Agent"), "concern": agent.get("risk", "Unspecified risk")})
    return items[:4]


def run_executive_orchestration(*, message: str, db: Optional[Session] = None, scope: str = "mission_control") -> Dict[str, Any]:
    intent = classify_intent(message)
    context_block = format_context_block(db=db, scope=scope) if db is not None else "No persistent executive context has been captured yet."
    context_available = "No persistent" not in context_block
    selected_agents = select_agents(message)
    selected_keys = {agent.key for agent in selected_agents}
    deliberation = run_board_room_deliberation(message=message, db=db, scope=scope)
    deliberation["agents"] = [agent for agent in deliberation.get("agents", []) if agent.get("agent") in selected_keys]
    risks = extract_risk_reviews(deliberation)
    confidence = confidence_score(intent, selected_agents, context_available, len(risks))
    stages = [stage_payload(stage, selected_agents, intent) for stage in STAGE_LIBRARY.get(intent, STAGE_LIBRARY["executive_strategy"])]
    consensus = deliberation.get("consensus", {})
    return {
        "mode": "autonomous_executive_orchestrator",
        "intent": intent,
        "scope": scope,
        "context_available": context_available,
        "context_excerpt": trim_text(context_block, 1000),
        "selected_agents": [asdict(agent) for agent in selected_agents],
        "stages": stages,
        "deliberation": deliberation,
        "risk_reviews": risks,
        "consensus": {
            "decision": consensus.get("decision", "Proceed only after a small, reversible, founder-approved proposal is clear."),
            "next_action": consensus.get("next_action", "Create a narrowly scoped engineering proposal before implementation."),
            "confidence": confidence,
            "confidence_label": "high" if confidence >= 0.78 else "medium" if confidence >= 0.6 else "low",
        },
        "orchestrator_action": {
            "type": "proposal_recommended" if intent in {"engineering_execution", "architecture_review"} else "decision_brief_recommended",
            "label": "Create founder-approved mission proposal" if intent in {"engineering_execution", "architecture_review"} else "Create executive decision brief",
            "requires_founder_approval": True,
        },
    }


def format_orchestration_markdown(orchestration: Dict[str, Any]) -> str:
    lines: List[str] = [
        "## Autonomous Executive Orchestrator",
        "",
        f"**Intent:** {orchestration.get('intent', '').replace('_', ' ')}",
        f"**Confidence:** {orchestration.get('consensus', {}).get('confidence_label')} ({orchestration.get('consensus', {}).get('confidence')})",
        f"**Context:** {'available' if orchestration.get('context_available') else 'not yet available'}",
        "",
        "### Selected Agents",
    ]
    for agent in orchestration.get("selected_agents", []):
        lines.append(f"- **{agent['title']}** — {agent['mandate']}")
    lines.extend(["", "### Orchestration Stages"])
    for stage in orchestration.get("stages", []):
        lines.append(f"- **{stage['stage'].replace('_', ' ').title()}**: {', '.join(stage.get('participants', []))}")
    lines.extend(["", "### Risk Reviews"])
    for item in orchestration.get("risk_reviews", []):
        lines.append(f"- **{item['agent']}**: {item['concern']}")
    consensus = orchestration.get("consensus", {})
    lines.extend(["", "### Consensus", f"**Decision:** {consensus.get('decision', '')}", f"**Next action:** {consensus.get('next_action', '')}"])
    return "\n".join(lines)
