from __future__ import annotations

from copy import deepcopy

from app.platform.architecture_agent.service import create_architecture_decision
from app.platform.architecture_agent.validator import validate_architecture_decision
from app.platform.capability_intelligence.service import discover_relevant_capabilities
from app.platform.repository_intelligence.service import inspect_repository_evidence


MISSION_ID = "MISSION-ARCH-01B-CHECK"
OBJECTIVE = "Make long-running Mission Control engineering work durable and independent of one browser HTTP request."


def main() -> None:
    capability_context = discover_relevant_capabilities(
        OBJECTIVE,
        {"validation_plan": ["python3 -m compileall app/platform"], "affected_files": ["app/platform/agents/worker.py"]},
        ["runtime", "events"],
        ["app/platform/agents/worker.py"],
    )
    repository = inspect_repository_evidence(
        ["app/platform/agents/worker.py"],
        requested_by="architecture-agent-check",
        relevance_by_path={"app/platform/agents/worker.py": "Durable worker execution evidence."},
        max_items=2,
    )
    bounded_repository = {
        "bounded": True,
        "manifest": repository["manifest"],
        "missing": repository["missing"],
    }
    result = create_architecture_decision({
        "mission_id": MISSION_ID,
        "objective": OBJECTIVE,
        "approved_plan": {"validation_plan": ["python3 -m compileall app/platform"]},
        "capability_context": capability_context,
        "repository_evidence": bounded_repository,
        "existing_constraints": ["No parallel mission identity or repository mutation."],
    })
    assert result["success"] is True, result
    artifact = result["architecture_decision"]
    assert artifact["status"] == "validated"
    assert artifact["mission_id"] == MISSION_ID
    assert artifact["capability_context_id"] == capability_context["capability_context_id"]
    assert artifact["capability_context_fingerprint"] == capability_context["context_fingerprint"]
    assert artifact["validation"]["valid"] is True
    assert bounded_repository["bounded"] is True and "context" not in bounded_repository

    capability_ids = {item["capability_id"] for item in capability_context["capabilities"]}
    expected = {"platform_agent_task", "workflow_run_persistence", "agent_worker", "execution_planner", "execution_bridge", "runtime_scheduler", "runtime_worker_pool", "platform_event_bus"}
    assert expected <= capability_ids, capability_ids
    decisions = artifact["decisions"]
    assert all(item["decision"] in {"REUSE", "EXTEND", "INTEGRATE", "NEW_COMPONENT_REQUIRED", "DEPRECATE", "RETIRE_AFTER_MIGRATION"} for item in decisions)
    assert not any(item["decision"] == "NEW_COMPONENT_REQUIRED" and "queue" in str(item.get("proposed_component", "")).lower() for item in decisions)
    event_bus = next(item for item in capability_context["capabilities"] if item["capability_id"] == "platform_event_bus")
    assert event_bus["production_status"] != "PRODUCTION_ACTIVE"
    pubsub = discover_relevant_capabilities("Inspect Pub/Sub event transport.", affected_domains=["infrastructure"])
    pubsub_record = next(item for item in pubsub["capabilities"] if item["capability_id"] == "pubsub")
    assert pubsub_record["production_status"] != "PRODUCTION_ACTIVE"

    empty_context = {
        "capability_context_id": "CAPCTX-ABSENT001",
        "context_fingerprint": "absent-context-fingerprint",
        "source_revision": capability_context["source_revision"],
        "capabilities": [],
    }
    new_result = create_architecture_decision({
        "mission_id": "MISSION-ARCH-NEW-CHECK",
        "objective": "Provide a capability absent from the bounded platform context.",
        "approved_plan": {"validation_plan": ["Validate the new bounded interface."]},
        "capability_context": empty_context,
        "repository_evidence": {"manifest": [], "missing": []},
        "proposed_component": {"name": "Controlled Missing Capability", "ownership": "Architecture Platform"},
    })
    assert new_result["success"] is True, new_result
    new_decision = new_result["architecture_decision"]["decisions"][0]
    assert new_decision["decision"] == "NEW_COMPONENT_REQUIRED"
    for field in ("capabilities_evaluated", "reuse_insufficiency", "extension_insufficiency", "integration_insufficiency", "ownership", "integration_contract", "required_validation"):
        assert new_decision.get(field), field

    invalid_new = deepcopy(new_result["architecture_decision"])
    invalid_new["decisions"][0].pop("reuse_insufficiency")
    invalid_validation = validate_architecture_decision(invalid_new, empty_context, {"manifest": []})
    assert invalid_validation["valid"] is False
    assert any("reuse_insufficiency" in error for error in invalid_validation["errors"])

    source_capability = next(item for item in capability_context["capabilities"] if item.get("implementation_evidence"))
    replacement = next(item for item in capability_context["capabilities"] if item["capability_id"] != source_capability["capability_id"])
    evidence_reference = next(
        item["source_reference"]
        for key, values in source_capability.items() if key.endswith("_evidence") and isinstance(values, (list, tuple))
        for item in values if item.get("source_reference")
    )
    deprecate = deepcopy(artifact)
    deprecate["decisions"] = [{
        "decision_id": "ARCHD-DEPRECATE-CHECK",
        "decision": "DEPRECATE",
        "capability_id": source_capability["capability_id"],
        "replacement_capability_id": replacement["capability_id"],
        "migration_implications": ["Migrate evidenced consumers before any retirement decision."],
        "unknown_consumer_scope": "Bounded scan does not prove global zero consumers.",
        "evidence_references": [evidence_reference],
        "remove_now": False,
    }]
    assert validate_architecture_decision(deprecate, capability_context, bounded_repository)["valid"] is True
    unsafe_deprecate = deepcopy(deprecate)
    unsafe_deprecate["decisions"][0].pop("replacement_capability_id")
    assert validate_architecture_decision(unsafe_deprecate, capability_context, bounded_repository)["valid"] is False
    unsafe_retire = deepcopy(deprecate)
    unsafe_retire["decisions"][0]["decision"] = "RETIRE_AFTER_MIGRATION"
    assert validate_architecture_decision(unsafe_retire, capability_context, bounded_repository)["valid"] is False

    corrected = create_architecture_decision({
        "mission_id": MISSION_ID,
        "objective": OBJECTIVE,
        "approved_plan": {"validation_plan": ["python3 -m compileall app/platform"]},
        "capability_context": capability_context,
        "repository_evidence": bounded_repository,
        "candidate_artifact": {"mission_id": MISSION_ID, "decisions": []},
    })
    assert corrected["success"] is True and corrected["correction_attempted"] is True
    print("PLATFORM-AWARE ARCHITECTURE AGENT CHECK PASSED")


if __name__ == "__main__":
    main()
