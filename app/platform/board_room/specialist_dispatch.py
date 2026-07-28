from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.platform.agents.registry import AgentDefinition, conversational_agents

_STOP_WORDS = {
    "about", "after", "again", "also", "because", "before", "being", "could",
    "founder", "from", "have", "into", "jarvis", "more", "please", "should",
    "that", "their", "there", "these", "this", "through", "with", "would",
    "your", "want", "like", "just", "able",
}
_MIN_SCORE = 2


def consult_matching_specialist(
    message: str,
    *,
    decomposition: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Best-effort: if the founder's request clearly matches a specific, chat-safe
    specialist agent's stated expertise, consult that agent synchronously and return
    a real result to fold into Jarvis's answer.

    Returns None whenever there is no confident match or the agent's own handler
    fails/declines - callers must treat this purely as an optional enrichment, never
    a requirement for producing a response.
    """
    agents = conversational_agents()
    if not agents:
        return None

    message_words = _keywords(message)
    if decomposition:
        message_words |= _keywords(str(decomposition.get("primary_objective") or ""))

    best_agent: Optional[AgentDefinition] = None
    best_score = 0
    for agent in agents:
        agent_words = _keywords(agent.name) | _keywords(agent.description)
        agent_words |= {
            word for capability in agent.capabilities for word in _keywords(capability.replace("_task", ""))
        }
        score = len(message_words & agent_words)
        if score > best_score:
            best_score = score
            best_agent = agent

    if not best_agent or best_score < _MIN_SCORE:
        return None

    task = {"input_payload": {"goal": message}, "description": message}
    try:
        result = best_agent.handler(task)
    except Exception:
        return None
    if not isinstance(result, dict) or not result.get("success"):
        return None

    return {
        "agent_id": best_agent.agent_id,
        "agent_name": best_agent.name,
        "match_score": best_score,
        "message": str(result.get("message") or "").strip(),
    }


def _keywords(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z][a-z-]{3,}", text.lower()) if word not in _STOP_WORDS}
