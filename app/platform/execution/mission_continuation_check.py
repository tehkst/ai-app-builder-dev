from __future__ import annotations

from unittest.mock import patch

from app.platform.execution.mission_continuation import continue_mission_to_production


MISSION_ID = "MISSION-AFOS-006"


def base_evidence() -> dict:
    return {
        "mission_id": MISSION_ID,
        "planning_result": {"status": "engineering-plan-created"},
        "architecture_review": {"status": "architecture-reviewed"},
        "engineering_handoff": {"status": "engineering-breakdown-created"},
        "executable_change_set": {"change_set_status": "change_set_ready"},
    }


def run(evidence: dict) -> dict:
    with patch("app.platform.execution.mission_continuation.get_execution_mission_evidence", return_value=evidence):
        return continue_mission_to_production({"mission_id": MISSION_ID})


def main() -> None:
    missing = continue_mission_to_production({})
    assert missing["status"] == "blocked"
    assert missing["current_stage"] == "mission_identity"

    repo_gate = run(base_evidence())
    assert repo_gate["current_stage"] == "repository_execution"
    assert repo_gate["approval_required"] is True
    assert repo_gate["approval_action"] == "github_execution"
    assert repo_gate["governance"]["read_only_projection"] is True

    pr_evidence = {
        **base_evidence(),
        "repository_execution": {"status": "pull-request-created"},
        "pr_lifecycle_result": {"mission_resolution_status": "resolved"},
    }
    ci_wait = run(pr_evidence)
    assert ci_wait["current_stage"] == "ci_validation"

    ci_failed = run({**pr_evidence, "ci_validation": {"status": "failed"}})
    assert ci_failed["current_stage"] == "ci_repair"
    assert ci_failed["recovery_action"] == "resume_ci_repair"

    merge_gate = run({
        **pr_evidence,
        "ci_validation": {"status": "passed"},
    })
    assert merge_gate["current_stage"] == "merge"
    assert merge_gate["approval_action"] == "merge"

    deploy_gate = run({
        **pr_evidence,
        "ci_validation": {"status": "passed"},
        "merge_result": {"status": "merged"},
    })
    assert deploy_gate["current_stage"] == "deployment"
    assert deploy_gate["approval_action"] == "deployment"

    deploy_failed = run({
        **pr_evidence,
        "ci_validation": {"status": "passed"},
        "merge_result": {"status": "merged"},
        "deployment_result": {"status": "failed"},
    })
    assert deploy_failed["current_stage"] == "deployment"
    assert deploy_failed["approval_required"] is False
    assert deploy_failed["recovery_action"] == "review_rollback_readiness"

    complete_evidence = {
        **pr_evidence,
        "ci_validation": {"status": "passed"},
        "merge_result": {"status": "merged"},
        "deployment_result": {"status": "deployed"},
        "production_verification": {"status": "verified"},
    }
    completed = run(complete_evidence)
    repeated = run(complete_evidence)
    assert completed["status"] == "mission-completed"
    assert completed["completion"]["verified_production"] is True
    assert repeated["current_stage"] == completed["current_stage"]
    assert repeated["completed_stages"] == completed["completed_stages"]
    assert completed["governance"]["source_systems_remain_authoritative"] is True
    assert completed["governance"]["separate_approvals_preserved"] is True

    print("AFOS-006 MISSION CONTINUATION CHECK PASSED")


if __name__ == "__main__":
    main()
