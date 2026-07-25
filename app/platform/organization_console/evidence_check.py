from __future__ import annotations

from unittest.mock import patch

from app.platform.organization_console.evidence import project_worker_evidence


def main() -> None:
    runtime = {
        "tasks": [{
            "task_id": "TASK-1",
            "title": "Implement mission",
            "status": "running",
            "priority": "high",
            "assigned_agent": "architect_agent",
            "parent_task_id": "RUN-1",
            "input_payload": {
                "mission_id": "MISSION-1",
                "stage": "architecture",
                "dependencies": ["TASK-0"],
                "collaborating_workers": ["backend_builder_agent"],
            },
            "result_payload": {"agent_id": "architect_agent"},
            "started_at": "2026-07-25T00:00:00+00:00",
            "updated_at": "2026-07-25T00:01:00+00:00",
        }],
        "runs": {
            "RUN-1": {
                "workflow_run_id": "RUN-1",
                "plan_status": "architecture",
                "metadata": {"mission_id": "MISSION-1"},
                "steps": [{
                    "handler_result": {
                        "mission_id": "MISSION-1",
                        "title": "Improve architecture",
                        "current_stage": "architecture",
                    }
                }],
            }
        },
        "execution_evidence": [{
            "evidence_id": "EXEC-1",
            "mission_id": "MISSION-1",
            "actor": "architect_agent",
            "capability": "create_pr",
            "outcome": "completed",
            "artifact": {
                "commit_sha": "abc123",
                "pull_request_url": "https://github.example/pr/1",
                "revision_name": "revision-1",
            },
            "created_at": "2026-07-25T00:02:00+00:00",
        }],
        "operational_evidence": [{
            "evidence_id": "OPS-1",
            "evidence_type": "production_verification",
            "authority": "production_verification_service",
            "scope": "MISSION-1",
            "status": "passed",
            "payload": {"worker": "architect_agent", "overall_result": "pass"},
            "observed_at": "2026-07-25T00:03:00+00:00",
        }],
    }
    source = {
        "found": True,
        "mission_id": "MISSION-1",
        "workflow_run_id": "RUN-1",
        "run": {"workflow_run_id": "RUN-1"},
        "state": {},
        "tasks": [],
        "events": [],
        "artifacts": [],
        "approvals": [],
    }
    lineage = [{
        "entry_id": "LINEAGE-1",
        "actor_id": "architect_agent",
        "summary": "Architecture decision recorded.",
        "event_type": "architecture_decision",
        "stage": "architecture",
        "status": "completed",
        "occurred_at": "2026-07-25T00:01:30+00:00",
        "artifact_refs": ["ADR-1"],
        "repository_refs": ["app/platform/example.py"],
        "deployment_refs": ["revision-1"],
        "authority": "DeliveryLineage",
    }]
    graph = {
        "nodes": [{
            "id": "component:example",
            "label": "Example component",
            "type": "component",
            "path": "app/platform/example.py",
        }],
        "edges": [],
    }
    with patch(
        "app.platform.organization_console.evidence.collect_sources",
        return_value=source,
    ), patch(
        "app.platform.organization_console.evidence.normalize_entries",
        return_value=lineage,
    ), patch(
        "app.platform.organization_console.evidence.build_graph",
        return_value=graph,
    ):
        result = project_worker_evidence("architect_agent", runtime)

    assignment = result["current_assignments"][0]
    assert assignment["mission_id"] == "MISSION-1", assignment
    assert assignment["workflow_run_id"] == "RUN-1", assignment
    assert assignment["execution_stage"] == "architecture", assignment
    assert "progress_percentage" not in assignment, assignment
    assert result["lineage_contributions"]["total"] == 1, result
    assert result["architecture_contributions"]["total"] == 1, result
    assert result["repository_contributions"]["total"] >= 2, result
    assert result["deployment_contributions"]["total"] >= 3, result
    assert result["activity"]["total"] >= 4, result
    print("AFOS-017A EVIDENCE INTEGRATION CHECK PASSED")


if __name__ == "__main__":
    main()
