from __future__ import annotations

import json
from copy import deepcopy

from app.platform.architecture_agent.service import create_architecture_decision
from app.platform.architecture_agent.validator import validate_architecture_decision
from app.platform.capability_intelligence.service import discover_relevant_capabilities


SANDBOX_CAPABILITIES = {
    "sandbox_workspace_materialization",
    "manual_browser_test_harness",
    "runtime_readiness_detector",
    "runtime_run_plan",
    "runtime_approval_gate",
    "controlled_sandbox_runtime",
    "runtime_log_capture",
    "runtime_failure_analysis",
    "hosted_sandbox_boundary",
}


def main() -> None:
    preproduction = discover_relevant_capabilities(
        "Before commissioning a generated application, safely run it in an isolated environment, capture runtime evidence, and analyse failures.",
        affected_domains=["sandbox"],
    )
    indexed = {item["capability_id"]: item for item in preproduction["capabilities"]}
    assert SANDBOX_CAPABILITIES <= set(indexed), set(indexed)
    assert all(indexed[capability_id]["implementation_evidence"] for capability_id in SANDBOX_CAPABILITIES)

    controlled = indexed["controlled_sandbox_runtime"]
    hosted = indexed["hosted_sandbox_boundary"]
    assert controlled["capability_id"] != hosted["capability_id"]
    assert "start_controlled_sandbox_runtime_for_workflow" in controlled["declared_interfaces"]
    assert hosted["declared_interfaces"] == ("inspect_hosted_sandbox_boundary",)
    assert not set(controlled["source_paths"]).intersection(hosted["source_paths"])

    twin_context = discover_relevant_capabilities(
        "Create a digital twin or pre-production behavioural simulation of an application so the factory can assess impact before commissioning.",
        affected_domains=["sandbox", "simulation"],
    )
    twin_ids = {item["capability_id"] for item in twin_context["capabilities"]}
    assert not any("digital_twin" in capability_id or capability_id == "digital_twin" for capability_id in twin_ids)
    assert {"controlled_sandbox_runtime", "runtime_readiness_detector", "materialization_dry_run", "workflow_step_simulation"} <= twin_ids
    assert len(twin_ids & {"materialization_dry_run", "workflow_step_simulation", "restore_impact_simulation", "repair_failure_simulation"}) >= 2

    architecture = create_architecture_decision({
        "mission_id": "MISSION-SANDBOX-AWARENESS",
        "objective": "Safely validate generated application behaviour before production commissioning.",
        "approved_plan": {"validation_plan": ["Run sandbox capability checks."]},
        "capability_context": twin_context,
        "repository_evidence": {"bounded": True, "manifest": [], "missing": []},
    })
    assert architecture["success"] is True, architecture
    decisions = architecture["architecture_decision"]["decisions"]
    decided_ids = {item.get("capability_id") for item in decisions}
    assert {"controlled_sandbox_runtime", "runtime_readiness_detector", "materialization_dry_run"} <= decided_ids
    assert not any(item["decision"] == "NEW_COMPONENT_REQUIRED" for item in decisions)

    generic_new = deepcopy(architecture["architecture_decision"])
    first_capability = twin_context["capabilities"][0]
    first_reference = next(
        item["source_reference"]
        for key, values in first_capability.items() if key.endswith("_evidence") and isinstance(values, (list, tuple))
        for item in values if item.get("source_reference")
    )
    generic_new["decisions"] = [{
        "decision_id": "ARCHD-UNSAFE-DIGITAL-TWIN",
        "decision": "NEW_COMPONENT_REQUIRED",
        "proposed_component": "Digital Twin",
        "capabilities_evaluated": [first_capability["capability_id"]],
        "reuse_insufficiency": "Generic insufficiency claim.",
        "extension_insufficiency": "Generic insufficiency claim.",
        "integration_insufficiency": "Generic insufficiency claim.",
        "ownership": "Unassigned",
        "integration_contract": "Unspecified",
        "lifecycle_responsibility": "Unassigned",
        "required_validation": ["Unspecified validation"],
        "migration_implications": ["Unknown"],
        "evidence_references": [first_reference],
    }]
    unsafe_validation = validate_architecture_decision(generic_new, twin_context, {"manifest": []})
    assert unsafe_validation["valid"] is False
    assert any("omits supplied relevant capabilities" in error for error in unsafe_validation["errors"])

    restore = discover_relevant_capabilities(
        "Simulate the impact of restoring a generated file version before performing the mutation.",
        affected_domains=["simulation"],
    )
    restore_ids = {item["capability_id"] for item in restore["capabilities"]}
    assert "restore_impact_simulation" in restore_ids
    restore_record = next(item for item in restore["capabilities"] if item["capability_id"] == "restore_impact_simulation")
    assert "simulate_generated_file_version_restore" in restore_record["declared_interfaces"]
    assert restore_record["implementation_evidence"]

    serialized = json.dumps({"preproduction": preproduction, "twin": twin_context, "restore": restore}, default=str)
    for forbidden in ("recommended_disposition", '"disposition"', "SUPERSEDE", "CONSOLIDATE", '"REMOVE"'):
        assert forbidden not in serialized
    print("SANDBOX AND SIMULATION ARCHITECTURE AWARENESS CHECK PASSED")


if __name__ == "__main__":
    main()
