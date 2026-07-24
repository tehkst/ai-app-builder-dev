from __future__ import annotations

from unittest.mock import patch

from app.platform.operating_console.delivery_contract import (
    add_existing_artifact,
    advance_contract,
    build_product_definition,
    build_ux_specification,
    create_delivery_contract,
    public_delivery_summary,
    record_founder_acceptance,
)


def run() -> None:
    context = {
        "mission_id": "MISSION-AFOS-013",
        "conversation_id": "CONVERSATION-AFOS-013",
        "founder_request": "Build a CRM for small transport companies.",
        "scope": {
            "objective": "Deliver one bounded CRM workflow.",
            "acceptance_criteria": ["Contacts and jobs persist."],
            "in_scope": ["Contact CRUD", "Job workflow"],
            "out_of_scope": ["Billing"],
            "governance_boundaries": ["No repository mutation without approval."],
        },
    }
    decision = {
        "decision_id": "DECISION-1",
        "selection_events": [{"event_id": "SELECTION-1"}],
        "assumptions": [
            {
                "id": "ASSUMPTION-1",
                "category": "customer",
                "current_value": "Small transport company",
                "state": "confirmed",
                "decision_impact": "high",
                "confidence": "high",
            }
        ],
    }
    contract = create_delivery_contract(
        context=context,
        workflow_run_id="MISSION-RUN-AFOS-013",
        decision_state=decision,
    )
    state = {"context": context, "delivery_contract": contract}
    product = build_product_definition(
        state=state,
        planning={
            "mission_id": context["mission_id"],
            "plan_id": "PLAN-1",
            "plan": {"scope": "Contact and job workflow", "dependencies": [], "risks": []},
        },
    )
    ux = build_ux_specification(state=state, product_definition=product)
    architecture = add_existing_artifact(
        state=state,
        artifact_type="architecture_decision",
        authority="architecture_agent",
        content={"status": "validated"},
        source_references=[product["artifact_id"], ux["artifact_id"]],
        evidence_references=["ADR-1"],
    )
    advance_contract(contract, "engineering_plan")

    assert contract["contract"] == "software-delivery-v1"
    assert contract["mission_identity"] == context["mission_id"]
    assert contract["workflow_run_identity"] == "MISSION-RUN-AFOS-013"
    assert contract["target_user"] == "Small transport company"
    assert contract["accepted_decision_references"] == ["DECISION-1", "SELECTION-1"]
    assert contract["product_definition_reference"] == product["artifact_id"]
    assert contract["ux_specification_reference"] == ux["artifact_id"]
    assert contract["architecture_decision_references"] == [architecture["artifact_id"]]
    assert contract["current_stage"] == "engineering_plan"

    accepted = record_founder_acceptance(
        contract,
        decision="accepted",
        actor="founder@example.com",
        action_id="ACTION-ACCEPT-1",
    )
    duplicate = record_founder_acceptance(
        contract,
        decision="accepted",
        actor="founder@example.com",
        action_id="ACTION-ACCEPT-1",
    )
    assert duplicate == accepted
    assert contract["current_stage"] == "complete"
    assert contract["founder_acceptance_reference"] == accepted["acceptance_id"]

    public = public_delivery_summary(contract)
    assert public
    assert len(public["artifacts"]) == 3
    assert "content" not in public["artifacts"][0]

    from app.platform.operating_console.action_service import build_decision_ready_mission_actions

    actions = build_decision_ready_mission_actions(
        context["founder_request"],
        conversation_id=context["conversation_id"],
    )
    action_context = actions["action_buttons"][0]["payload"]["action_context"]
    assert action_context["conversation_id"] == context["conversation_id"]

    with patch(
        "app.platform.founder_decision.service.load_decision_experience",
        return_value=decision,
    ):
        from app.platform.operating_console.mission_run_service import (
            _load_founder_decision_state,
        )

        assert _load_founder_decision_state(action_context) == decision

    print("AFOS-013 DELIVERY CONTRACT CHECK PASSED")


if __name__ == "__main__":
    run()
