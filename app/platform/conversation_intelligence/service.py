from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_conversation_intelligence_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "AI Conversation Intelligence Engine",
        "milestone": "CI-01",
        "status": "conversation-intelligence-ready",
        "endpoint": "POST /mission-control/conversation-intelligence/analyze",
    }


def analyze_conversation(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("message") or payload.get("request") or payload.get("prompt") or "")
    lowered = text.lower()
    if any(word in lowered for word in ["deploy", "production", "rollback"]):
        mode = "Deployment"
    elif any(word in lowered for word in ["implement", "build", "fix", "execute", "github", "pr", "pull request"]):
        mode = "Engineering Mission"
    elif any(word in lowered for word in ["architecture", "duplicate", "root cause", "refactor"]):
        mode = "Architecture"
    elif any(word in lowered for word in ["audit", "review", "check", "validate"]):
        mode = "Review"
    elif any(word in lowered for word in ["explain", "clarify", "why", "what is"]):
        mode = "Knowledge"
    else:
        mode = "General Conversation"
    mission_required = mode in {"Engineering Mission", "Deployment"}
    decisions = []
    actions = []
    knowledge = []
    for sentence in [s.strip(" -•\t") for s in text.replace("\n", ". ").split(".") if s.strip()]:
        s = sentence.lower()
        if any(word in s for word in ["approval", "must", "should", "avoid", "preserve"]):
            decisions.append(sentence)
        if any(word in s for word in ["audit", "identify", "produce", "implement", "execute", "review"]):
            actions.append(sentence)
        if any(word in s for word in ["mission control", "board room", "github", "gcp", "login", "authentication", "duplicate"]):
            knowledge.append(sentence)
    if mode in {"Engineering Mission", "Architecture", "Review"}:
        actions.extend(["Run repository audit and identify affected files.", "Produce phased implementation plan and small PR plan."])
    return {
        "company": "AI Software Factory",
        "product": "AI Conversation Intelligence Engine",
        "milestone": "CI-01",
        "status": "conversation-intelligence-ready",
        "conversation_intelligence": {
            "mode": mode,
            "confidence": 0.9 if mission_required else 0.72,
            "decisions": decisions[:8],
            "actions": actions[:8],
            "knowledge": knowledge[:8],
            "mission_required": mission_required,
            "mission_suggestion": {
                "suggested": mission_required,
                "title": (mode + ": " + text[:60]).strip(),
            },
            "recommended_next_action": "Generate workflow and ask Founder to approve, edit, or reject." if mission_required else "Continue discussion or save as working note.",
            "analyzed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }
