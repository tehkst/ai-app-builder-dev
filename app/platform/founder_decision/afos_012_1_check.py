from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.platform.founder_decision.builder import build_decision_experience
from app.platform.persistence.models import PlatformBase


def _state(conversation_id: str = "AFOS-012-1-CHECK"):
    return build_decision_experience(
        conversation_id=conversation_id,
        founder_message="Build a CRM for small transport companies.",
        response_text=(
            "Start with owner-led transport operators running 5-50 vehicles and "
            "prove one enquiry-to-payment workflow."
        ),
        mode="Product Discovery",
        decisions=[],
        actions=[],
        mission_proposals=[],
        history=[],
    )


def _durable_selection_check() -> None:
    import app.platform.founder_decision.service as service

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PlatformBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    original_session = service.PlatformSessionLocal
    original_tables = service.create_platform_tables
    original_auth = service.require_founder
    service.PlatformSessionLocal = session
    service.create_platform_tables = lambda: None
    service.require_founder = lambda payload: {"authorized": True}
    try:
        state = _state()
        service.save_decision_experience(state)
        request = state["decision_request"]
        payload = {
            "token": "validation-only",
            "conversation_id": state["conversation_id"],
            "expected_version": state["version"],
            "action": "change_assumption",
            "target_id": request["assumption_id"],
            "value": request["options"][0],
            "interaction_source": "chat",
            "source_message_id": "MSG-CHECK",
            "action_id": "AFOS-012-1-SELECTION-ONCE",
        }
        result = service.apply_decision_action(payload)
        event = result["founder_selection"]
        assert event["conversation_id"] == state["conversation_id"]
        assert event["source_message_id"] == "MSG-CHECK"
        assert event["interaction_source"] == "chat"
        assert event["previous_value"].startswith("The first customer")
        assert event["new_value"] == request["options"][0]
        assert result["continuation"]["message"].startswith("Understood.")
        assert "Executive Brief updated" not in result["continuation"]["message"]
        assert len(result["decision_experience"]["selection_events"]) == 1

        duplicate = service.apply_decision_action(payload)
        assert duplicate["idempotent"] is True
        assert len(duplicate["decision_experience"]["selection_events"]) == 1
        assert duplicate["founder_selection"]["event_id"] == event["event_id"]
        assert duplicate["continuation"]["message"]

        natural_state = _state("AFOS-012-1-NATURAL")
        service.save_decision_experience(natural_state)
        natural = service.apply_natural_language_selection(
            {
                "token": "validation-only",
                "message": natural_state["decision_request"]["options"][0],
            },
            natural_state,
        )
        assert natural is not None
        assert natural["founder_selection"]["interaction_source"] == "natural_language"
        assert natural["continuation"]["message"].startswith("Understood.")
    finally:
        service.PlatformSessionLocal = original_session
        service.create_platform_tables = original_tables
        service.require_founder = original_auth


def _progressive_decision_check() -> None:
    import app.platform.founder_decision.service as service

    state = _state("AFOS-012-1-PROGRESSIVE")
    first = state["decision_request"]
    service._transition(
        state,
        "change_assumption",
        {
            "target_id": first["assumption_id"],
            "value": first["options"][0],
        },
    )
    continuation = service._natural_continuation(
        "change_assumption", first["options"][0], state
    )
    assert continuation["active_decision"] is not None
    assert continuation["active_decision"]["assumption_id"] != first["assumption_id"]
    assert len(
        [
            item
            for item in [state.get("decision_request")]
            if item and item.get("state") == "open"
        ]
    ) == 1


def _browser_contract_check() -> None:
    from app.platform.ui.founder_dashboard_board_chat import (
        render_board_chat_dashboard,
    )

    html = render_board_chat_dashboard()
    assert "streamMsg(data.board_room_response||founderResponse" in html
    assert "null,thinking)" in html
    assert "if(thinking&&thinking.parentNode)thinking.remove()" not in html
    assert "Executive Brief updated:" not in html
    assert "window.addFounderDecisionChoice" in html
    assert "window.completeFounderDecisionContinuation" in html
    assert "interaction_source:source||'executive_brief'" in html
    assert "Current decision" in html
    assert "Decision progress" in html
    assert "More context" in html
    assert "aria-label','Jarvis is thinking'" in html
    assert "aria-label','Jarvis response complete'" in html


def main() -> None:
    _durable_selection_check()
    _progressive_decision_check()
    _browser_contract_check()
    print("AFOS-012.1 conversational workflow acceptance: PASS")


if __name__ == "__main__":
    main()
