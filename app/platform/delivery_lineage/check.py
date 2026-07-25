from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

from app.platform.delivery_lineage.causality import link_causality
from app.platform.delivery_lineage.causality import relationships
from app.platform.delivery_lineage.entries import normalize_entries
from app.platform.delivery_lineage.gaps import detect_gaps
from app.platform.delivery_lineage.security import sanitize_entries
from app.platform.delivery_lineage.service import build_delivery_lineage, build_lineage_summary
from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard
from app.platform.ui.delivery_lineage_script import render_delivery_lineage_script


def main() -> None:
    source = _source()
    entries = sanitize_entries(link_causality(normalize_entries(source)))
    assert [item["sequence"] for item in entries] == list(range(1, len(entries) + 1))
    assert len({item["entry_id"] for item in entries}) == len(entries)
    repair = next(item for item in entries if "repair" in item["stage"])
    assert repair["caused_by_entry_id"] is not None
    assert repair["causality"] == "proven"
    assert all(item.get("provider") == "deepseek" for item in entries)
    assert all(item.get("model") == "deepseek-v4-pro" for item in entries)
    assert "secret" not in str(entries).lower()
    assert any(item["type"] == "derives_from" for item in relationships(entries))

    gaps = detect_gaps(source, entries)
    assert gaps["classification"] == "complete", gaps

    with patch("app.platform.delivery_lineage.service.require_founder", return_value={"authorized": True}), patch(
        "app.platform.delivery_lineage.service.collect_sources", return_value=source
    ):
        first = build_delivery_lineage({"token": "secret"})
        second = build_delivery_lineage({"token": "secret", "mode": "causal"})
        failures = build_delivery_lineage({"token": "secret", "failures_only": True})
    assert first["contract"] == "autonomous-delivery-lineage-v1"
    assert first["mission"]["mission_id"] == "MISSION-LINEAGE"
    assert first["workflow_run"]["workflow_run_id"] == "MISSION-RUN-LINEAGE"
    assert first["provider_model"]["provider"] == "deepseek"
    assert first["provider_model"]["model"] == "deepseek-v4-pro"
    assert second["entry_count"] == first["entry_count"]
    assert failures["filtered_entry_count"] >= 2
    assert first["cache"]["used"] is False
    assert first["mutation_enabled"] is False

    missing = deepcopy(source)
    missing["state"]["context"].pop("provider")
    missing["state"]["context"].pop("model")
    assert detect_gaps(missing, link_causality(normalize_entries(missing)))["classification"] == "partial"

    release = deepcopy(source)
    release["state"]["delivery_contract"]["production_verification_reference"] = "DELIVERY-VERIFY-C"
    release["execution_evidence"] = [
        {
            "capability": "merge_pr", "outcome": "success", "requested_action": "merge_pr",
            "evidence_id": "EXEC-MERGE", "created_at": "2026-07-24T00:07:00+00:00",
            "actor": "mission_control", "artifacts": {"merge_commit_sha": "abc123"},
            "authorization": {"governing_policy": "capability-authority-separation-v1"},
        },
        {
            "capability": "deploy", "outcome": "success", "requested_action": "deploy",
            "evidence_id": "EXEC-DEPLOY", "created_at": "2026-07-24T00:08:00+00:00",
            "actor": "mission_control", "artifacts": {"revision_name": "afos-app-check-00001-abc"},
            "authorization": {"governing_policy": "capability-authority-separation-v1"},
        },
    ]
    release_entries = link_causality(normalize_entries(release))
    assert any(item.get("deployment_refs") for item in release_entries)
    assert detect_gaps(release, release_entries)["classification"] == "complete"

    with patch("app.platform.delivery_lineage.service.require_founder", return_value={"authorized": False}):
        denied = build_delivery_lineage({"token": "secret"})
    assert denied["status"] == "unauthorized"
    capability = build_lineage_summary()
    assert capability["authenticated_query_required"] is True
    assert "mission_id" not in capability
    dashboard = render_stable_founder_dashboard()
    assert 'data-section="lineage"' in dashboard
    assert 'id="lineageEntries"' in dashboard
    assert "/mission-control/delivery-lineage/query" in dashboard
    assert "JSON.stringify(data)" not in render_delivery_lineage_script()
    print("AFOS-015 autonomous delivery lineage checks passed")


def _source():
    contract = {
        "founder_objective": "Prepare the bounded CRM mission.",
        "current_stage": "change_set_ready",
        "approval_state": {"mission": "approved"},
        "next_governed_action": "Founder review required",
        "produced_artifact_references": ["DELIVERY-PLAN-A", "DELIVERY-CHANGE-B"],
        "validation_evidence_references": ["VALIDATION-1"],
        "release_evidence_references": [],
        "production_verification_reference": None,
        "founder_acceptance_reference": None,
        "artifacts": [
            {
                "artifact_id": "DELIVERY-PLAN-A", "artifact_type": "engineering_plan",
                "status": "ready", "authoring_authority": "engineering_manager",
                "created_at": "2026-07-24T00:01:00+00:00", "source_references": [],
                "evidence_references": [], "content": {},
            },
            {
                "artifact_id": "DELIVERY-CHANGE-B", "artifact_type": "change_set",
                "status": "ready", "authoring_authority": "native_coding_agent",
                "created_at": "2026-07-24T00:05:00+00:00",
                "source_references": ["DELIVERY-PLAN-A"], "evidence_references": ["VALIDATION-1"],
                "content": {},
            },
        ],
    }
    return {
        "found": True, "mission_id": "MISSION-LINEAGE", "workflow_run_id": "MISSION-RUN-LINEAGE",
        "run": {
            "workflow_run_id": "MISSION-RUN-LINEAGE", "workflow_name": "Durable Board Room Mission Run",
            "status": "change_set_ready", "plan_status": "change_set_ready",
            "created_at": "2026-07-24T00:00:00+00:00", "updated_at": "2026-07-24T00:06:00+00:00",
        },
        "state": {
            "mission_id": "MISSION-LINEAGE", "status": "change_set_ready",
            "title": "Bounded CRM", "founder_request": "Prepare a CRM.",
            "context": {"provider": "deepseek", "model": "deepseek-v4-pro", "provider_source": "runtime-provider-router"},
            "delivery_contract": contract,
            "steps": [
                {"stage": "validation", "status": "failed", "summary": "Structural validation failed.", "at": "2026-07-24T00:03:00+00:00"},
                {"stage": "change_set_repair", "status": "completed", "summary": "Bounded repair completed.", "at": "2026-07-24T00:04:00+00:00"},
                {"stage": "change_set_ready", "status": "completed", "summary": "Validation passed.", "at": "2026-07-24T00:06:00+00:00"},
            ],
        },
        "tasks": [{
            "task_id": "TASK-1", "title": "Generate change set", "status": "completed",
            "task_type": "approved_mission_stage", "requested_by": "mission_runtime",
            "assigned_agent": "native_coding_agent", "input": {"stage": "change_set"},
            "result": {}, "error": "provider token=secret was not logged", "approval_required": False, "approval_id": None,
            "parent_task_id": "MISSION-RUN-LINEAGE", "attempts": 1, "max_attempts": 3,
            "created_at": "2026-07-24T00:02:00+00:00", "started_at": "2026-07-24T00:02:10+00:00",
            "completed_at": "2026-07-24T00:06:00+00:00", "failed_at": None,
        }],
        "events": [], "execution_evidence": [], "approvals": [], "operational_evidence": [],
    }


if __name__ == "__main__":
    main()
