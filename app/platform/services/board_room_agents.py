from __future__ import annotations

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
    BoardRoomAgent(
        key="ceo",
        title="CEO",
        mandate="Decide whether this advances the company vision, customer value, and execution focus.",
        lens="vision, sequencing, founder leverage, company-building clarity",
    ),
    BoardRoomAgent(
        key="cto",
        title="CTO",
        mandate="Assess technical architecture, implementation risk, maintainability, and deployment safety.",
        lens="architecture, production stability, reviewable PRs, technical debt",
    ),
    BoardRoomAgent(
        key="cfo",
        title="CFO",
        mandate="Assess cost, ROI, funding impact, runway, and whether the work compounds enterprise value.",
        lens="ROI, burn, pricing leverage, investor-grade discipline",
    ),
    BoardRoomAgent(
        key="cmo",
        title="CMO",
        mandate="Assess market positioning, founder story, user clarity, and GTM implications.",
        lens="positioning, adoption, messaging, customer pull",
    ),
    BoardRoomAgent(
        key="coo",
        title="COO",
        mandate="Assess operational feasibility, sequencing, handoffs, and process reliability.",
        lens="execution systems, workflow hygiene, operational simplicity",
    ),
    BoardRoomAgent(
        key="cso",
        title="Chief Strategy Officer",
        mandate="Assess competitive advantage, wedge, market timing, and strategic narrative.",
        lens="moat, sequencing, strategic trade-offs, category creation",
    ),
    BoardRoomAgent(
        key="counsel",
        title="General Counsel",
        mandate="Assess governance, approval boundaries, privacy, security, and production risk.",
        lens="governance, protected auth boundary, data handling, compliance posture",
    ),
    BoardRoomAgent(
        key="vc_partner",
        title="VC Partner",
        mandate="Assess whether this makes the company more fundable and more obviously venture-scale.",
        lens="venture narrative, speed, defensibility, market size, proof points",
    ),
    BoardRoomAgent(
        key="devil_advocate",
        title="Devil's Advocate",
        mandate="Challenge assumptions, identify failure modes, and expose hidden complexity.",
        lens="risks, contradictions, premature scale, wasted motion",
    ),
)


def _trim(text: str, limit: int = 900) -> str:
    return (text or "").strip()[:limit]


def _classify_intent(message: str) -> str:
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


def run_board_room_deliberation(
    *,
    message: str,
    db: Optional[Session] = None,
    scope: str = "mission_control",
) -> Dict[str, Any]:
    context_block = format_context_block(db=db, scope=scope) if db is not None else "No persistent executive context has been captured yet."
    agent_positions = [_agent_position(agent, message, context_block) for agent in BOARD_ROOM_AGENTS]

    risks = [item["risk"] for item in agent_positions[:4]]
    consensus = {
        "decision": "Proceed only as a small founder-approved mission with explicit scope and rollback path.",
        "why": "The Board Room agents agree that the next step should increase product differentiation while preserving production stability.",
        "risks": risks,
        "next_action": "Create or review a narrowly scoped engineering proposal before implementation.",
    }

    return {
        "mode": "true_multi_agent_board_room",
        "scope": scope,
        "context_available": "No persistent" not in context_block,
        "context_excerpt": _trim(context_block, 1200),
        "agents": agent_positions,
        "consensus": consensus,
    }


def format_deliberation_markdown(deliberation: Dict[str, Any]) -> str:
    lines: List[str] = ["## Multi-Agent Board Room Deliberation", ""]
    for agent in deliberation.get("agents", []):
        lines.extend(
            [
                f"### {agent['title']}",
                f"**Position:** {agent['position']}",
                f"**Recommendation:** {agent['recommendation']}",
                f"**Risk:** {agent['risk']}",
                "",
            ]
        )
    consensus = deliberation.get("consensus", {})
    lines.extend(
        [
            "## Consensus Recommendation",
            f"**Decision:** {consensus.get('decision', '')}",
            f"**Why:** {consensus.get('why', '')}",
            f"**Next action:** {consensus.get('next_action', '')}",
        ]
    )
    return "\n".join(lines)
