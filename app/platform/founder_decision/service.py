from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.platform.auth.service import require_founder
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformContextStore


KIND = "founder_decision_state"
SOURCE = "founder_decision_experience"
LOGGER = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _selection_label(action: str, payload: Dict[str, Any], state: Dict[str, Any]) -> str:
    value = str(payload.get("value") or "").strip()
    if value:
        return value
    labels = {
        "accept_recommendation": "Use Jarvis's recommendation",
        "change_recommendation": "Change the recommendation",
        "show_alternatives": "Show alternatives",
        "defer_decision": "Skip for now",
        "challenge_recommendation": "Challenge the recommendation",
        "confirm_assumption": "Use the current working assumption",
        "reject_assumption": "Reject the working assumption",
        "explain_assumption": "Why does this matter?",
    }
    if action == "select_alternative":
        target = str(payload.get("target_id") or "")
        alternative = next(
            (
                item for item in state.get("alternatives") or []
                if str(item.get("id") or "") == target
            ),
            {},
        )
        return str(alternative.get("label") or "Use this alternative")
    return labels.get(action, action.replace("_", " ").capitalize())


def _previous_selection_value(state: Dict[str, Any], payload: Dict[str, Any]) -> Any:
    target = str(payload.get("target_id") or "")
    assumption = next(
        (
            item for item in state.get("assumptions") or []
            if str(item.get("id") or "") == target
        ),
        None,
    )
    if assumption:
        return assumption.get("statement")
    return (state.get("decision_request") or {}).get("selected_option")


def _active_decision(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request = state.get("decision_request")
    if isinstance(request, dict) and request.get("state") == "open":
        return request
    return None


def _advance_decision(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    current = _active_decision(state)
    if current:
        return current
    unresolved = sorted(
        (
            item for item in state.get("assumptions") or []
            if item.get("state") == "proposed"
        ),
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}.get(
                str(item.get("decision_impact") or "low"), 3
            ),
            {"low": 0, "medium": 1, "high": 2}.get(
                str(item.get("confidence") or "medium"), 3
            ),
        ),
    )
    if not unresolved:
        state["decision_request"] = None
        return None
    assumption = unresolved[0]
    request = {
        "id": "clarification-%s" % assumption["id"],
        "question": "Which option should Jarvis use as the working assumption?",
        "assumption_id": assumption["id"],
        "options": assumption.get("options") or [],
        "reason": "This choice has the greatest effect on the current recommendation.",
        "state": "open",
    }
    state["decision_request"] = request
    return request


def _natural_continuation(
    action: str,
    selection: str,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    next_decision = _advance_decision(state)
    if action == "challenge_recommendation":
        challenge = state.get("challenge") or {}
        text = "%s %s" % (
            str(challenge.get("counterargument") or "I tested the recommendation."),
            str(
                challenge.get("decision_changing_condition")
                or "I will keep the current recommendation until stronger evidence changes it."
            ),
        )
    elif action == "show_alternatives":
        strongest = next(iter(state.get("alternatives") or []), {})
        text = (
            "The strongest alternative is %s. It becomes preferable when its customer "
            "or workflow evidence is stronger than the current recommendation."
            % str(strongest.get("label") or "not yet supported by enough evidence")
        )
    elif action == "defer_decision":
        text = "Understood. I will leave that choice open and continue with the parts that do not depend on it."
    elif action == "explain_assumption":
        text = "This matters because changing it would materially alter the first scope and how we validate demand."
    else:
        text = "Understood. I will use %s as the working choice." % selection
    if next_decision:
        text += "\n\n%s" % str(next_decision.get("question") or "")
    elif action not in {"challenge_recommendation", "show_alternatives", "explain_assumption"}:
        text += "\n\nI now have enough confirmed context to prepare a bounded mission for your review."
    return {
        "message": text,
        "active_decision": next_decision,
        "mission_ready": next_decision is None,
    }


def _selection_event(
    state: Dict[str, Any],
    action: str,
    payload: Dict[str, Any],
    previous_value: Any,
    new_value: Any,
) -> Dict[str, Any]:
    action_id = str(payload.get("action_id") or "")
    event_id = hashlib.sha256(
        ("%s:%s" % (state.get("conversation_id"), action_id)).encode("utf-8")
    ).hexdigest()[:20]
    return {
        "event_id": "SELECTION-%s" % event_id.upper(),
        "conversation_id": state.get("conversation_id"),
        "source_message_id": payload.get("source_message_id"),
        "decision_id": state.get("decision_id"),
        "assumption_id": payload.get("target_id"),
        "selected_option_id": payload.get("option_id") or payload.get("target_id"),
        "previous_value": previous_value,
        "new_value": new_value,
        "interaction_source": str(payload.get("interaction_source") or "executive_brief"),
        "event_timestamp": _now(),
        "version": int(state.get("version") or 0) + 1,
        "idempotency_key": action_id,
        "action": action,
    }


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


def apply_natural_language_selection(
    payload: Dict[str, Any],
    state: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    request = _active_decision(state)
    if not request:
        return None
    message = str(payload.get("message") or "").strip()
    normalized = " ".join(message.lower().split())
    action = ""
    value = ""
    if normalized in {"use your recommendation", "use jarvis's recommendation", "use jarvis recommendation"}:
        action = "confirm_assumption"
    elif normalized in {"skip", "skip for now", "defer", "decide later"}:
        action = "defer_decision"
    elif normalized in {"why", "why?", "why does this matter"}:
        action = "explain_assumption"
    else:
        for option in request.get("options") or []:
            option_text = str(option)
            if normalized == " ".join(option_text.lower().split()):
                action = "change_assumption"
                value = option_text
                break
    if not action:
        return None
    action_payload = {
        "token": payload.get("token"),
        "conversation_id": state.get("conversation_id"),
        "expected_version": state.get("version"),
        "action": action,
        "target_id": request.get("assumption_id"),
        "value": value,
        "interaction_source": "natural_language",
        "source_message_id": payload.get("source_message_id"),
        "action_id": "%s:%s:natural:%s" % (
            state.get("conversation_id"),
            state.get("version"),
            hashlib.sha256(message.encode("utf-8")).hexdigest()[:12],
        ),
    }
    return apply_decision_action(action_payload)


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
            prior_event = next(
                (
                    item for item in reversed(state.get("selection_events") or [])
                    if item.get("idempotency_key") == action_id
                ),
                None,
            )
            selection = str(
                (prior_event or {}).get("new_value")
                or _selection_label(action, payload, state)
            )
            return {
                "status": "unchanged",
                "idempotent": True,
                "decision_experience": state,
                "founder_selection": prior_event,
                "continuation": _natural_continuation(action, selection, state),
            }
        expected = payload.get("expected_version")
        if expected is not None and int(expected) != int(state.get("version") or 0):
            return {
                "status": "conflict",
                "error": "This decision changed in another session. Refresh the Executive Brief.",
                "decision_experience": state,
            }
        selection = _selection_label(action, payload, state)
        previous_value = _previous_selection_value(state, payload)
        _transition(state, action, payload)
        continuation = _natural_continuation(action, selection, state)
        events = list(state.get("selection_events") or [])
        events.append(
            _selection_event(state, action, payload, previous_value, selection)
        )
        state["selection_events"] = events[-100:]
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
        LOGGER.info(
            "founder_selection conversation_id=%s source=%s active_decisions=%d "
            "selection_events=%d continuation_ready=%s",
            conversation_id,
            events[-1]["interaction_source"],
            1 if continuation["active_decision"] else 0,
            len(events),
            bool(continuation["message"]),
        )
        return {
            "status": "updated",
            "authenticated": True,
            "decision_experience": state,
            "founder_selection": events[-1],
            "continuation": continuation,
            "interaction_metrics": {
                "active_decision_count": 1 if continuation["active_decision"] else 0,
                "decisions_shown_simultaneously": 1 if continuation["active_decision"] else 0,
                "founder_selection_source": events[-1]["interaction_source"],
                "selection_event_count": len(events),
                "robotic_fallback_used": False,
                "state_divergence_detected": False,
            },
        }
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
        request = state.get("decision_request") or {}
        request["state"] = "deferred"
        for assumption in state.get("assumptions") or []:
            if assumption.get("id") == request.get("assumption_id"):
                assumption["state"] = "deferred"
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
        request = state.get("decision_request") or {}
        request["state"] = "resolved"
        request["selected_option"] = next(
            (
                item.get("label") for item in state.get("alternatives") or []
                if item.get("id") == target
            ),
            None,
        )
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
