from __future__ import annotations

import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.platform.board_room.founder_conversation_contract import FounderConversationContract
from app.platform.board_room.founder_response_composer import FounderResponseComposer
from app.platform.founder_decision.builder import build_decision_experience
from app.platform.persistence.models import PlatformBase


def _response(prompt: str, mode: str = "PRODUCT_DISCOVERY") -> tuple:
    contract = FounderConversationContract._contract(
        mode,
        "Prepare a founder decision",
        mode == "EXECUTION_REQUEST",
    )
    response = FounderResponseComposer.compose(
        founder_message=prompt,
        draft="",
        contract=contract,
        context={},
        conversation_history=[],
    )
    state = build_decision_experience(
        conversation_id="TEST-%s" % uuid.uuid4().hex,
        founder_message=prompt,
        response_text=response.text,
        mode=mode.replace("_", " ").title(),
        decisions=response.decisions,
        actions=response.actions,
        mission_proposals=response.mission_proposals,
        history=[],
    )
    return response, state


def _acceptance_scenarios() -> None:
    # draft="" forces FounderResponseComposer's fallback path deliberately, to test
    # build_decision_experience()'s own real logic (AssumptionEngine inference runs
    # on founder_message, never on response.text, so it is unaffected either way) -
    # NOT to test specific fallback wording. A prior version of this test asserted
    # exact hardcoded strings ("5-50 vehicles", "Jarvis intelligence first") that
    # only existed because founder_response_composer.py's fallback used to contain
    # per-topic canned answers keyed on these exact test messages' keywords - a real
    # smell (the fallback existed to make THIS test pass, not to serve a founder),
    # confirmed and removed this session. The fallback is now one honest, generic
    # message regardless of topic - assert that, not topic-specific content.
    crm, crm_state = _response("I want to build a CRM for small transport companies.")
    assert "could not produce a verified, reviewed answer" in crm.text
    assert crm_state["assumptions"][0]["decision_impact"] == "high"
    assert crm_state["decision_request"]["assumption_id"] == "target_customer"
    assert crm_state["mission_proposals"]

    school, school_state = _response("Build me a school management system.")
    assert "could not produce a verified, reviewed answer" in school.text
    assert len([
        item for item in school_state["assumptions"]
        if item["decision_impact"] == "high"
    ]) == 1
    assert len(school_state["decision_request"]["options"]) >= 2

    priority, priority_state = _response(
        "Should we improve Jarvis intelligence, improve the UI, build stronger "
        "code generation, or build Digital Twin testing first?",
        "STRATEGIC_ADVICE",
    )
    assert "could not produce a verified, reviewed answer" in priority.text
    assert priority_state["recommendation"]["statement"]
    assert priority_state["trade_offs"]

    from app.platform.founder_decision.service import _transition
    original = priority_state["recommendation"]["statement"]
    _transition(priority_state, "challenge_recommendation", {})
    assert priority_state["challenge"]["counterargument"]
    assert priority_state["challenge"]["decision_changing_condition"]
    assert priority_state["recommendation"]["statement"] == original

    generic, generic_state = _response("Build a CRM.")
    assert generic_state["decision_request"]
    target = generic_state["decision_request"]["assumption_id"]
    _transition(generic_state, "confirm_assumption", {"target_id": target})
    assert generic_state["decision_request"]["state"] == "resolved"
    _transition(generic_state, "change_assumption", {
        "target_id": target,
        "value": "Mid-market operations team",
    })
    assert "Mid-market" in generic_state["recommendation"]["rationale"]

    effort, effort_state = _response("What should we do before building?")
    assert any(item["owner"] == "Jarvis" for item in effort_state["actions"])
    assert not any(item["owner"] == "Founder" for item in effort_state["actions"])
    assert "prepare" in effort_state["actions"][0]["title"].lower()

    proposal = crm_state["mission_proposals"][0]
    assert proposal["approval_state"] == "not_approved"
    assert any(
        item["label"] == "Approve Mission"
        for item in proposal["governed_actions"]["action_buttons"]
    )

    information = FounderConversationContract._contract(
        "INFORMATION_REQUEST", "Answer directly", False
    )
    simple = FounderResponseComposer.compose(
        founder_message="What does SaaS mean?",
        draft="SaaS means software delivered as an online service, usually for a subscription.",
        contract=information,
        context={},
    )
    assert not simple.decisions and not simple.actions and not simple.mission_proposals


def _persistence_and_conflict_checks() -> None:
    import app.platform.founder_decision.service as service

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PlatformBase.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)
    original_session = service.PlatformSessionLocal
    original_tables = service.create_platform_tables
    original_auth = service.require_founder
    service.PlatformSessionLocal = test_session
    service.create_platform_tables = lambda: None
    service.require_founder = lambda payload: {"authorized": True, "role": "founder"}
    try:
        _, first = _response("Build a CRM.")
        first["conversation_id"] = "conversation-one"
        service.save_decision_experience(first)
        assert service.load_decision_experience("conversation-one")["decision_id"] == first["decision_id"]
        assert service.load_decision_experience("conversation-two") is None

        payload = {
            "token": "test",
            "conversation_id": "conversation-one",
            "expected_version": 1,
            "action": "accept_recommendation",
            "action_id": "accept-once",
        }
        accepted = service.apply_decision_action(payload)
        assert accepted["decision_experience"]["recommendation"]["state"] == "accepted"
        duplicate = service.apply_decision_action(payload)
        assert duplicate["idempotent"] is True
        conflict = service.apply_decision_action({
            **payload,
            "action_id": "different-action",
        })
        assert conflict["status"] == "conflict"
    finally:
        service.PlatformSessionLocal = original_session
        service.create_platform_tables = original_tables
        service.require_founder = original_auth


def _frontend_contract() -> None:
    from app.platform.ui.founder_dashboard_board_chat import render_board_chat_dashboard

    html = render_board_chat_dashboard()
    for marker in (
        "Decision Workspace",
        "Accept",
        "Challenge",
        "Show alternatives",
        "Current decision",
        "Decision progress",
        "data-fd-mission",
        "aria-live",
        "data-fd-action",
        "conversation_id:activeSession",
    ):
        assert marker in html, marker
    assert "No decisions captured yet." not in html
    assert "No actions captured yet." not in html


def main() -> None:
    _acceptance_scenarios()
    _persistence_and_conflict_checks()
    _frontend_contract()
    print("AFOS-012 founder decision acceptance: PASS")


if __name__ == "__main__":
    main()
