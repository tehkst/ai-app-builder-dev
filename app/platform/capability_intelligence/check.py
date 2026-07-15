from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import fields

from app.platform.capability_intelligence.service import (
    EvidenceItem,
    _DiscoveryHint,
    _derive_statuses,
    discover_relevant_capabilities,
    get_capability_context,
    get_capability_intelligence_status,
)
from app.platform.registry.registry import base_registry


def _item(evidence_type: str) -> EvidenceItem:
    return EvidenceItem(evidence_type, "fixture.py", "Bounded fixture evidence.", "abc123", "HIGH")


def main() -> None:
    status = get_capability_intelligence_status()
    sources = status["sources"]
    assert status["mutation_enabled"] is False
    assert status["mode"] == "read-only-evidence-derived-aggregator"
    assert sources["agent_manifest_registry"] > 0 and sources["delegated_capabilities"] > 0
    assert sources["plugins"] > 0 and sources["providers"] > 0 and sources["event_types"] > 0
    assert sources["company_intelligence"] == sources["company_brain"] == sources["executive_context"] == 1
    assert status["record_count"] > len(base_registry())

    hint_fields = {field.name for field in fields(_DiscoveryHint)}
    forbidden_hint_fields = {"lifecycle", "integration", "production", "disposition", "recommended_disposition"}
    assert not hint_fields & forbidden_hint_fields, hint_fields

    complete_index = {"scope": {"complete_within_root": True}}
    implementation = [_item("IMPLEMENTATION")]
    lifecycle, integration, production, _, _ = _derive_statuses(implementation, [], [], [], [], [], complete_index)
    assert lifecycle == "FOUNDATION" and integration == "DISCONNECTED"
    lifecycle, integration, _, _, _ = _derive_statuses(implementation, [], [_item("CONSUMER_REFERENCE")], [], [], [], complete_index)
    assert lifecycle == "FOUNDATION" and integration == "IMPLEMENTED"
    lifecycle, integration, _, _, _ = _derive_statuses(implementation, [], [_item("CONSUMER_REFERENCE")], [_item("EXECUTION_PATH_REFERENCE")], [], [], complete_index)
    assert lifecycle == "INTEGRATED" and integration == "INTEGRATED"
    _, _, production, _, _ = _derive_statuses(implementation, [], [], [], [], [], complete_index)
    assert production != "PRODUCTION_ACTIVE"

    runtime = discover_relevant_capabilities(
        "Make long-running Mission Control work durable through queued workers, workflow continuation, and recovery.",
        {"requirements": ["persist work", "use capability-aware specialist execution", "observe failures"]},
        ["runtime", "events"],
        ["app/platform/services/agent_task_service/part_4.py"],
    )
    ids = {item["capability_id"] for item in runtime["capabilities"]}
    expected = {
        "platform_agent_task", "workflow_run_persistence", "agent_worker", "execution_planner",
        "execution_bridge", "runtime_scheduler", "platform_event_bus",
    }
    assert expected <= ids, ids
    assert not any("frontend_builder" in item or "application_builder" in item for item in ids), ids
    assert runtime["bounded"] is True and runtime["capability_count"] <= 16
    task = next(item for item in runtime["capabilities"] if item["capability_id"] == "platform_agent_task")
    assert task["implementation_evidence"]
    assert task["consumer_evidence"]

    declarations = discover_relevant_capabilities(
        "Inspect the platform_core plugin, workflow provider, and job.failed event type.",
        affected_domains=["plugins", "providers"],
    )
    declaration_ids = {item["capability_id"] for item in declarations["capabilities"]}
    assert {"plugin_platform_core_plugin", "provider_workflow_provider", "event_type_job_failed"} <= declaration_ids

    event_context = get_capability_context(["platform_event_bus", "pubsub", "platform_agent_task"])
    indexed = {item["capability_id"]: item for item in event_context["capabilities"]}
    event_bus = indexed["platform_event_bus"]
    assert event_bus["lifecycle_classification"] == "FOUNDATION"
    assert event_bus["implementation_evidence"] and not event_bus["execution_path_evidence"]
    assert indexed["pubsub"]["lifecycle_classification"] == "PLACEHOLDER"
    assert indexed["pubsub"]["declaration_evidence"] and not indexed["pubsub"]["implementation_evidence"]
    assert indexed["platform_agent_task"]["overlap_evidence"]

    serialized = json.dumps(event_context, sort_keys=True)
    for forbidden in ("recommended_disposition", '"disposition"', "SUPERSEDE", "CONSOLIDATE"):
        assert forbidden not in serialized

    repeated = get_capability_context(["platform_agent_task", "platform_event_bus"])
    first = get_capability_context(["platform_event_bus", "platform_agent_task"])
    assert repeated["context_fingerprint"] == first["context_fingerprint"]
    assert repeated["capability_context_id"] == first["capability_context_id"]
    reordered = discover_relevant_capabilities(
        "Inspect durable runtime evidence.", affected_domains=["events", "runtime"],
        affected_paths=["app/platform/events/event_bus.py", "app/platform/agents/worker.py"],
    )
    ordered = discover_relevant_capabilities(
        "Inspect durable runtime evidence.", affected_domains=["runtime", "events"],
        affected_paths=["app/platform/agents/worker.py", "app/platform/events/event_bus.py"],
    )
    assert reordered["context_fingerprint"] == ordered["context_fingerprint"]

    before = deepcopy(base_registry())
    get_capability_intelligence_status()
    assert base_registry() == before
    print("CAPABILITY INTELLIGENCE CHECK PASSED")


if __name__ == "__main__":
    main()
