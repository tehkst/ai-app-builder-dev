from __future__ import annotations

import tempfile
from pathlib import Path
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

    completed_result = {
        "status": "verified_diff_ready",
        "mission_id": context["mission_id"],
        "agent_task_id": "AGENT-TASK-DETERMINISTIC",
    }
    with patch(
        "app.platform.coding_agent.integration.NATIVE_CODING_AGENT_ENABLED",
        True,
    ), patch(
        "app.platform.coding_agent.integration._load_agent_task_result",
        return_value=completed_result,
    ), patch(
        "app.platform.coding_agent.integration._create_agent_task",
    ) as create_task:
        from app.platform.coding_agent.integration import route_mission_to_coding_agent

        reused = route_mission_to_coding_agent(
            {
                "mission_id": context["mission_id"],
                "workflow_run_id": "MISSION-RUN-AFOS-013",
                "agent_task_id": "AGENT-TASK-DETERMINISTIC",
            }
        )
    assert reused == completed_result
    create_task.assert_not_called()

    from app.platform.coding_agent.github_compat import verified_diff_file_changes
    from app.platform.coding_agent.models import ChangedFile, VerifiedDiff

    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        (root / "app").mkdir()
        (root / "app/example.py").write_text("VALUE = 1\n", encoding="utf-8")
        diff = VerifiedDiff(
            mission_id=context["mission_id"],
            workflow_run_id="MISSION-RUN-AFOS-013",
            agent_task_id="AGENT-TASK-DETERMINISTIC",
            workspace_id="WORKSPACE-AFOS-013",
            status="verified_diff_ready",
            base_ref="main",
            base_sha="base",
            head_tree_fingerprint="tree",
            iterations=1,
            changed_files=[
                ChangedFile(path="app/example.py", operation="update"),
                ChangedFile(path="app/obsolete.py", operation="delete"),
            ],
        )
        with patch(
            "app.platform.workspaces.execution_service.inspect_workspace",
            return_value={"status": "released", "local_path": workspace},
        ):
            changes = verified_diff_file_changes(diff)
        assert changes == [
            {"path": "app/example.py", "operation": "write", "content": "VALUE = 1\n"},
            {"path": "app/obsolete.py", "operation": "delete"},
        ]

    durable_state = {
        "found": True,
        "workflow_run_id": "MISSION-RUN-AFOS-013",
        "mission_id": context["mission_id"],
        "context": context,
        "approval": {"status": "approved"},
        "status": "change_set_ready",
        "current_stage": "change_set_ready",
        "steps": [],
        "delivery_contract": create_delivery_contract(
            context=context,
            workflow_run_id="MISSION-RUN-AFOS-013",
            decision_state=decision,
        ),
        "change_set": {
            "native_coding_agent": {
                "repository_execution": {
                    "execution": {
                        "mission_id": context["mission_id"],
                        "write_batch": changes,
                    }
                }
            }
        },
        "error": None,
    }
    from app.platform.operating_console import mission_run_service

    with patch.object(
        mission_run_service,
        "load_mission_run",
        return_value=durable_state,
    ), patch.object(
        mission_run_service,
        "_persist",
    ) as persist, patch.object(
        mission_run_service,
        "_task_snapshot",
        return_value={"count": 0, "current": None},
    ):
        with patch.object(
            mission_run_service,
            "require_founder",
            return_value={"authorized": True, "email": "founder@example.com"},
        ):
            package = mission_run_service.get_repository_execution_package(
                {
                    "token": "session",
                    "mission_id": durable_state["mission_id"],
                    "workflow_run_id": durable_state["workflow_run_id"],
                }
            )
        assert package["repository_execution"]["execution"]["write_batch"] == changes

        transitions = [
            (
                "github_execution",
                "PR-42",
                {"status": "pull-request-created", "pull_request_number": 42},
                "pull_request",
            ),
            (
                "pr_lifecycle",
                "PR-42-PASS",
                {"status": "pr-status-ready", "checks_summary": {"overall": "passing"}},
                "merge_approval",
            ),
            (
                "approved_merge",
                "MERGE-1",
                {"status": "pr-merged", "merge_commit_sha": "abc123"},
                "deployment_approval",
            ),
            (
                "cloud_run_deployment",
                "REV-1",
                {"status": "deployment-completed", "revision_name": "revision-1"},
                "production_verification",
            ),
            (
                "production_verification",
                "VERIFY-1",
                {"overall_result": "pass", "evidence_id": "VERIFY-1"},
                "founder_acceptance",
            ),
        ]
        for authority, event_key, evidence, expected_stage in transitions:
            result = mission_run_service.record_delivery_authority_result(
                workflow_run_id=durable_state["workflow_run_id"],
                mission_id=durable_state["mission_id"],
                authority=authority,
                evidence=evidence,
                event_key=event_key,
            )
            assert result["progress"]["current_stage"] == expected_stage
        event_count = len(durable_state["delivery_events"])
        duplicate = mission_run_service.record_delivery_authority_result(
            workflow_run_id=durable_state["workflow_run_id"],
            mission_id=durable_state["mission_id"],
            authority="production_verification",
            evidence={"overall_result": "pass", "evidence_id": "VERIFY-1"},
            event_key="VERIFY-1",
        )
        assert duplicate["reused"] is True
        assert len(durable_state["delivery_events"]) == event_count

        delayed_pr = mission_run_service.record_delivery_authority_result(
            workflow_run_id=durable_state["workflow_run_id"],
            mission_id=durable_state["mission_id"],
            authority="pr_lifecycle",
            evidence={
                "status": "pr-status-ready",
                "checks_summary": {"overall": "failing"},
            },
            event_key="PR-42-LATE-FAILURE",
        )
        assert delayed_pr["progress"]["current_stage"] == "founder_acceptance"

        with patch.object(
            mission_run_service,
            "require_founder",
            return_value={"authorized": True, "email": "founder@example.com"},
        ):
            acceptance = mission_run_service.record_release_acceptance(
                {
                    "token": "session",
                    "mission_id": durable_state["mission_id"],
                    "workflow_run_id": durable_state["workflow_run_id"],
                    "action": "accept_release",
                    "action_id": "ACCEPT-1",
                }
            )
            repeated_acceptance = mission_run_service.record_release_acceptance(
                {
                    "token": "session",
                    "mission_id": durable_state["mission_id"],
                    "workflow_run_id": durable_state["workflow_run_id"],
                    "action": "accept_release",
                    "action_id": "ACCEPT-1",
                }
            )
        assert acceptance["progress"]["current_stage"] == "complete"
        assert acceptance["reused"] is False
        assert repeated_acceptance["reused"] is True
        assert persist.call_count >= len(transitions) + 1

    print("AFOS-013 DELIVERY CONTRACT CHECK PASSED")


if __name__ == "__main__":
    run()
