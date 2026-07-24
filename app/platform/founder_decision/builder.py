from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.founder_decision.assumption_engine import AssumptionEngine
from app.platform.operating_console.action_service import build_decision_ready_mission_actions


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identifier(conversation_id: str, kind: str, text: str) -> str:
    digest = hashlib.sha256(
        ("%s:%s:%s" % (conversation_id, kind, text)).encode("utf-8")
    ).hexdigest()[:12]
    return "%s-%s" % (kind.upper(), digest.upper())


def _first_paragraph(text: str) -> str:
    return next((part.strip() for part in text.split("\n\n") if part.strip()), text.strip())


def _recommendation(text: str) -> Dict[str, Any]:
    summary = _first_paragraph(text)
    return {
        "statement": summary,
        "rationale": "This is the strongest bounded next step supported by the current conversation.",
        "state": "proposed",
        "confidence": "medium",
        "founder_decision_needed": True,
    }


def _alternatives(assumptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not assumptions:
        return []
    options = assumptions[0].get("options") or []
    return [
        {
            "id": "alternative-%d" % (index + 1),
            "label": str(option),
            "best_use_case": "Use this when evidence favors a different initial customer or workflow.",
            "benefit": "Tests a materially different interpretation of the opportunity.",
            "drawback": "Requires revising the current working assumption.",
            "consequence": "The first scope and validation plan will change.",
            "rank": index + 2,
            "state": "available",
        }
        for index, option in enumerate(options[1:3])
    ]


def build_decision_experience(
    *,
    conversation_id: str,
    founder_message: str,
    response_text: str,
    mode: str,
    decisions: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
    mission_proposals: List[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
    provider: Any = None,
    model: Any = None,
) -> Dict[str, Any]:
    assumptions = AssumptionEngine().infer(founder_message, history or [])
    recommendation = _recommendation(response_text)
    decision_id = _identifier(conversation_id, "decision", recommendation["statement"])
    alternatives = _alternatives(assumptions)
    decision_request = None
    material = next(
        (item for item in assumptions if item.get("decision_impact") == "high"),
        None,
    )
    if material:
        decision_request = {
            "id": "clarification-%s" % material["id"],
            "question": "Which option should Jarvis use as the working assumption?",
            "assumption_id": material["id"],
            "options": material.get("options") or [],
            "reason": "This choice materially changes the recommended scope.",
            "state": "open",
        }
    prepared_actions = []
    for index, item in enumerate(actions[:3]):
        title = str(item.get("action") if isinstance(item, dict) else item)
        if title.lower().startswith("review the recommendation"):
            title = "Prepare the evidence needed to validate this recommendation."
        if "interview " in title.lower():
            title = "Prepare the target profiles, research guide, and evidence scorecard."
        prepared_actions.append({
            "id": _identifier(conversation_id, "action", str(item)),
            "title": title,
            "owner": "Jarvis",
            "state": "proposed",
            "approval_required": False,
            "expected_result": "Decision evidence prepared for founder review.",
            "founder_effort": "Decision only",
            "sequence": index + 1,
        })
    if not prepared_actions and mode not in {"Casual Conversation", "Information Request"}:
        prepared_actions.append({
            "id": _identifier(conversation_id, "action", founder_message),
            "title": "Prepare the evidence needed to validate this recommendation.",
            "owner": "Jarvis",
            "state": "proposed",
            "approval_required": False,
            "expected_result": "A decision-ready evidence package.",
            "founder_effort": "Review the result",
            "sequence": 1,
        })
    proposals = []
    for item in mission_proposals[:1]:
        objective = str(item.get("objective") or founder_message)
        proposals.append({
            "id": _identifier(conversation_id, "mission", objective),
            "title": objective[:180],
            "objective": objective,
            "scope": str(item.get("scope") or "Bounded planning and validation"),
            "expected_output": str(item.get("expected_output") or "A founder-reviewed scope and validation plan."),
            "ai_departments": ["Product", "Engineering"],
            "estimated_sequence": ["Prepare", "Review", "Approve"],
            "state": "proposed",
            "approval_state": "not_approved",
            "governed_actions": build_decision_ready_mission_actions(
                objective,
                provider=provider,
                model=model,
                conversation_id=conversation_id,
            ),
        })
    if not proposals and mode in {
        "Product Discovery",
        "Project Planning",
        "Execution Request",
    }:
        objective = "Validate and prepare: %s" % founder_message[:160]
        proposals.append({
            "id": _identifier(conversation_id, "mission", objective),
            "title": objective,
            "objective": objective,
            "scope": "Jarvis prepares evidence, a bounded scope, and validation criteria before engineering.",
            "expected_output": "A decision-ready validation package and bounded mission scope.",
            "ai_departments": ["Product", "Research", "Engineering"],
            "estimated_sequence": ["Prepare evidence", "Founder review", "Mission approval"],
            "state": "proposed",
            "approval_state": "not_approved",
            "governed_actions": build_decision_ready_mission_actions(
                objective,
                provider=provider,
                model=model,
                conversation_id=conversation_id,
            ),
        })
    return {
        "contract": "founder-decision-v1",
        "conversation_id": conversation_id,
        "version": 1,
        "decision_id": decision_id,
        "mode": mode,
        "recommendation": recommendation,
        "assumptions": assumptions,
        "alternatives": alternatives,
        "trade_offs": [
            {
                "gain": "Faster evidence from a bounded first move.",
                "sacrifice": "Adjacent opportunities remain deferred until the evidence is clear.",
            }
        ] if alternatives else [],
        "risks": [
            {
                "id": "risk-assumption",
                "statement": "The recommendation may change if a high-impact assumption is wrong.",
                "level": "medium" if material else "low",
                "likelihood": "possible" if material else "unlikely",
                "impact": "high" if material else "low",
                "state": "open",
                "mitigation": "Jarvis will validate the assumption before consequential execution.",
            }
        ],
        "decision_request": decision_request,
        "actions": prepared_actions,
        "mission_proposals": proposals,
        "knowledge": decisions[:2],
        "follow_up": {
            "prompt": "Challenge the recommendation or choose a working assumption.",
        },
        "challenge": None,
        "founder_effort": {
            "principle": "Jarvis prepares; the founder decides.",
            "required_actions": 1 if decision_request else 0,
        },
        "selection_events": [],
        "processed_actions": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
