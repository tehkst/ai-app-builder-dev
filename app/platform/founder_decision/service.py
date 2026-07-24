from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.platform.auth.service import require_founder
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformContextStore


KIND = "founder_decision_state"
SOURCE = "founder_decision_experience"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scope(conversation_id: str) -> str:
    return "founder_decision:%s" % conversation_id[:80]


def _load_record(db: Any, conversation_id: str) -> Optional[Any]:
    return (
        db.query(PlatformContextStore)
        .filter(
            PlatformContextStore.scope == _scope(conversation_id),
            PlatformContextStore.kind == KIND,
        )
        .order_by(PlatformContextStore.updated_at.desc())
        .first()
    )


def load_decision_experience(conversation_id: str) -> Optional[Dict[str, Any]]:
    if not conversation_id:
        return None
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        record = _load_record(db, conversation_id)
        return json.loads(record.body) if record else None
    finally:
        db.close()


def save_decision_experience(state: Dict[str, Any]) -> Dict[str, Any]:
    conversation_id = str(state.get("conversation_id") or "").strip()
    if not conversation_id:
        raise ValueError("conversation_id is required")
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        record = _load_record(db, conversation_id)
        body = json.dumps(state, sort_keys=True, separators=(",", ":"))
        if record:
            record.body = body
            record.title = str(
                (state.get("recommendation") or {}).get("statement")
                or "Founder decision"
            )[:240]
            record.source = SOURCE
        else:
            record = PlatformContextStore(
                scope=_scope(conversation_id),
                kind=KIND,
                title=str(
                    (state.get("recommendation") or {}).get("statement")
                    or "Founder decision"
                )[:240],
                body=body,
                source=SOURCE,
            )
            db.add(record)
        db.commit()
        return state
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_decision_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not require_founder(payload).get("authorized"):
        return {"status": "unauthorized", "authenticated": False}
    conversation_id = str(payload.get("conversation_id") or "").strip()
    if not conversation_id:
        return {"status": "invalid-request", "error": "conversation_id is required"}
    state = load_decision_experience(conversation_id)
    return {
        "status": "found" if state else "not-found",
        "authenticated": True,
        "decision_experience": state,
    }


def apply_decision_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not require_founder(payload).get("authorized"):
        return {"status": "unauthorized", "authenticated": False}
    conversation_id = str(payload.get("conversation_id") or "").strip()
    action = str(payload.get("action") or "").strip()
    action_id = str(payload.get("action_id") or "").strip()
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        record = (
            db.query(PlatformContextStore)
            .filter(
                PlatformContextStore.scope == _scope(conversation_id),
                PlatformContextStore.kind == KIND,
            )
            .with_for_update()
            .first()
        )
        if not record:
            return {"status": "not-found", "error": "Decision experience was not found."}
        state = json.loads(record.body)
        if action_id and action_id in (state.get("processed_actions") or []):
            return {"status": "unchanged", "idempotent": True, "decision_experience": state}
        expected = payload.get("expected_version")
        if expected is not None and int(expected) != int(state.get("version") or 0):
            return {
                "status": "conflict",
                "error": "This decision changed in another session. Refresh the Executive Brief.",
                "decision_experience": state,
            }
        _transition(state, action, payload)
        state["version"] = int(state.get("version") or 0) + 1
        state["updated_at"] = _now()
        processed = list(state.get("processed_actions") or [])
        if action_id:
            processed.append(action_id)
        state["processed_actions"] = (processed[-40:])
        record.body = json.dumps(state, sort_keys=True, separators=(",", ":"))
        record.title = str(
            (state.get("recommendation") or {}).get("statement")
            or "Founder decision"
        )[:240]
        db.commit()
        return {"status": "updated", "authenticated": True, "decision_experience": state}
    except ValueError as exc:
        db.rollback()
        return {"status": "invalid-request", "error": str(exc)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _transition(state: Dict[str, Any], action: str, payload: Dict[str, Any]) -> None:
    recommendation = state.get("recommendation") or {}
    if action == "accept_recommendation":
        recommendation["state"] = "accepted"
    elif action == "change_recommendation":
        recommendation["state"] = "reconsidering"
    elif action == "show_alternatives":
        state["alternatives_visible"] = True
    elif action == "defer_decision":
        recommendation["state"] = "deferred"
    elif action == "challenge_recommendation":
        alternatives = state.get("alternatives") or []
        strongest = alternatives[0] if alternatives else None
        state["challenge"] = {
            "counterargument": (
                "The strongest alternative is %s." % strongest.get("label")
                if strongest
                else "The available evidence is not strong enough to prefer a different path yet."
            ),
            "decision_changing_condition": "Choose the alternative if new evidence disproves the highest-impact assumption.",
            "revised_confidence": "low" if not strongest else "medium",
        }
    elif action in {"confirm_assumption", "change_assumption", "reject_assumption"}:
        target = str(payload.get("target_id") or "")
        for assumption in state.get("assumptions") or []:
            if assumption.get("id") == target:
                assumption["state"] = {
                    "confirm_assumption": "confirmed",
                    "change_assumption": "changed",
                    "reject_assumption": "rejected",
                }[action]
                if action == "change_assumption":
                    assumption["statement"] = str(payload.get("value") or assumption["statement"])
                request = state.get("decision_request") or {}
                if request.get("assumption_id") == target:
                    request["state"] = "resolved"
                    request["selected_option"] = assumption.get("statement")
                recommendation["state"] = "revised" if action != "confirm_assumption" else recommendation.get("state", "proposed")
                recommendation["rationale"] = (
                    "Updated using the founder-reviewed working assumption: %s"
                    % assumption.get("statement")
                )
    elif action == "explain_assumption":
        target = str(payload.get("target_id") or "")
        for assumption in state.get("assumptions") or []:
            if assumption.get("id") == target:
                assumption["explanation"] = (
                    "This is surfaced because confidence is %s and changing it has %s impact on scope."
                    % (assumption.get("confidence"), assumption.get("decision_impact"))
                )
    elif action == "select_alternative":
        target = str(payload.get("target_id") or "")
        for alternative in state.get("alternatives") or []:
            alternative["state"] = "selected" if alternative.get("id") == target else "available"
        recommendation["state"] = "reconsidering"
    elif action in {
        "approve_action", "assign_ai", "assign_founder", "complete_action",
        "defer_action", "edit_action", "reject_action",
    }:
        target = str(payload.get("target_id") or "")
        for item in state.get("actions") or []:
            if item.get("id") == target:
                if action.startswith("assign_"):
                    item["owner"] = "Jarvis" if action == "assign_ai" else "Founder"
                elif action == "approve_action":
                    item["state"] = "approved"
                elif action == "complete_action":
                    item["state"] = "completed"
                elif action == "edit_action":
                    item["title"] = str(payload.get("value") or item["title"])
                else:
                    item["state"] = "deferred" if action == "defer_action" else "rejected"
    elif action in {"accept_risk", "mitigate_risk"}:
        target = str(payload.get("target_id") or "")
        for risk in state.get("risks") or []:
            if risk.get("id") == target:
                risk["state"] = "accepted" if action == "accept_risk" else "mitigating"
    else:
        raise ValueError("Unsupported founder decision action.")
