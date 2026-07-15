from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.platform.agents.manifest_registry import all_manifests
from app.platform.agents.registry import list_agents
from app.platform.delegation.capability_index import capability_map
from app.platform.events.event_registry import event_registry
from app.platform.plugins.plugin_registry import plugin_registry
from app.platform.plugins.provider_registry import provider_registry
from app.platform.registry.registry import base_registry
from app.platform.repository_intelligence.service import inspect_repository_evidence


REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_REFERENCE_FILES = 800
MAX_REFERENCE_FILE_CHARS = 120_000
LIFECYCLE_CLASSIFICATIONS = ("INTEGRATED", "FOUNDATION", "PLACEHOLDER", "UNKNOWN")
INTEGRATION_STATUSES = ("IMPLEMENTED", "INTEGRATED", "DISCONNECTED", "PLACEHOLDER", "UNKNOWN")
PRODUCTION_STATUSES = ("PRODUCTION_ACTIVE", "PRODUCTION_CONFIGURED", "PRODUCTION_UNPROVEN", "UNKNOWN")

LIFECYCLE_SEMANTICS = {
    "INTEGRATED": "Material implementation and a non-test canonical execution-path reference were evidenced.",
    "FOUNDATION": "Material implementation was evidenced, but canonical execution integration was not.",
    "PLACEHOLDER": "Only a deferred/declarative artifact was evidenced and no material implementation was found.",
    "UNKNOWN": "The bounded evidence is insufficient for a stronger lifecycle conclusion.",
}
INTEGRATION_SEMANTICS = {
    "IMPLEMENTED": "Material implementation and consumers were evidenced, but no canonical execution path was evidenced.",
    "INTEGRATED": "Material implementation and a canonical execution-path consumer were evidenced.",
    "DISCONNECTED": "Material implementation exists and a complete bounded reference scan found no external consumer.",
    "PLACEHOLDER": "Only deferred/declarative evidence was found.",
    "UNKNOWN": "Inspection coverage or evidence is insufficient to establish integration.",
}
PRODUCTION_SEMANTICS = {
    "PRODUCTION_ACTIVE": "Capability-specific runtime activation evidence was inspected.",
    "PRODUCTION_CONFIGURED": "Capability-specific production configuration, but no activation evidence, was inspected.",
    "PRODUCTION_UNPROVEN": "No capability-specific activation evidence was found in the bounded evidence.",
    "UNKNOWN": "Production evidence could not be inspected reliably.",
}


@dataclass(frozen=True)
class EvidenceItem:
    evidence_type: str
    source_reference: str
    fact: str
    fingerprint: str | None
    confidence: str


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    canonical_name: str
    domain: str
    purpose: str
    owning_layer: str
    lifecycle_classification: str
    integration_status: str
    production_status: str
    declared_interfaces: tuple[str, ...]
    declared_capabilities: tuple[str, ...]
    source_paths: tuple[str, ...]
    implementation_evidence: tuple[EvidenceItem, ...]
    declaration_evidence: tuple[EvidenceItem, ...]
    consumer_evidence: tuple[EvidenceItem, ...]
    dependency_evidence: tuple[EvidenceItem, ...]
    integration_evidence: tuple[EvidenceItem, ...]
    execution_path_evidence: tuple[EvidenceItem, ...]
    production_configuration_evidence: tuple[EvidenceItem, ...]
    production_activation_evidence: tuple[EvidenceItem, ...]
    overlap_evidence: tuple[EvidenceItem, ...]
    inspection_scope: dict[str, Any]
    unknowns: tuple[str, ...]
    evidence_fingerprint: str
    confidence: str


@dataclass(frozen=True)
class _DiscoveryHint:
    capability_id: str
    canonical_name: str
    domain_hint: str
    purpose_hint: str
    owning_layer_hint: str
    candidate_paths: tuple[str, ...]
    candidate_interfaces: tuple[str, ...] = ()
    declared_capabilities: tuple[str, ...] = ()
    dependency_hints: tuple[str, ...] = ()
    overlap_hints: tuple[str, ...] = ()
    production_configuration_paths: tuple[str, ...] = ()
    production_activation_paths: tuple[str, ...] = ()


_SYSTEM_DISCOVERY_HINTS = (
    _DiscoveryHint("company_intelligence", "Company Intelligence", "company", "Current company and platform operating context.", "company_intelligence", ("app/platform/company_intelligence/service.py",), ("build_company_intelligence_snapshot",), ("company_context", "capability_inventory")),
    _DiscoveryHint("company_brain", "Company Brain", "company", "Repository-backed company knowledge.", "company_brain", ("app/platform/company_brain/service.py", "app/platform/company_brain/repository.py"), declared_capabilities=("company_knowledge",)),
    _DiscoveryHint("executive_context", "Executive Context", "company", "Bounded persistent executive context.", "executive_context", ("app/platform/services/executive_context_service.py",), ("list_context_items", "format_context_block", "capture_context"), ("executive_context",), ("persistence",)),
    _DiscoveryHint("platform_agent_task", "PlatformAgentTask", "runtime", "Durable agent task and status evidence.", "workflow_runtime", ("app/platform/persistence/model_definitions/agents.py", "app/platform/services/agent_task_service/part_4.py"), ("PlatformAgentTask", "claim_next_agent_task"), ("durable_task", "agent_task_queue"), ("persistence", "agent_manifest_registry"), ("runtime_job", "runtime_job_queue")),
    _DiscoveryHint("workflow_run_persistence", "Workflow Run Persistence", "runtime", "Durable workflow and step progress evidence.", "workflow_runtime", ("app/platform/services/workflow_run_persistence_service.py",), ("persist_workflow_result", "get_workflow_run_detail"), ("workflow_persistence", "step_persistence"), ("persistence",)),
    _DiscoveryHint("agent_worker", "Agent Worker", "runtime", "Claims tasks and invokes registered handlers.", "workflow_runtime", ("app/platform/agents/worker.py",), ("execute_one_task", "run_loop"), ("worker_process", "task_claim"), ("platform_agent_task", "agent_registry"), ("runtime_worker_pool",)),
    _DiscoveryHint("execution_planner", "Agent Execution Planner", "runtime", "Capability-aware dependency execution planning.", "workflow_runtime", ("app/platform/services/agent_execution_planner_service.py",), ("build_agent_execution_plan",), ("execution_planning", "dependency_order"), ("agent_manifest_registry", "capability_discovery")),
    _DiscoveryHint("execution_bridge", "Agent Execution Bridge", "runtime", "Controlled registered-specialist invocation boundary.", "workflow_runtime", ("app/platform/services/agent_execution_bridge_service.py",), ("execute_agent_via_bridge",), ("specialist_invocation", "execution_audit"), ("agent_registry",), ("direct_specialist_invocation",)),
    _DiscoveryHint("runtime_job", "RuntimeJob", "runtime", "Runtime job state model.", "runtime_foundation", ("app/platform/runtime/job.py", "app/platform/runtime/execution_engine.py"), ("RuntimeJob",), ("job_state",), overlap_hints=("platform_agent_task",)),
    _DiscoveryHint("runtime_job_queue", "Runtime Job Queue", "runtime", "Runtime job ordering and queue operations.", "runtime_foundation", ("app/platform/runtime/job_queue.py",), declared_capabilities=("job_queue",), overlap_hints=("platform_agent_task",)),
    _DiscoveryHint("runtime_scheduler", "Runtime Scheduler", "runtime", "Queued-job and worker selection.", "runtime_foundation", ("app/platform/runtime/runtime_scheduler.py",), declared_capabilities=("scheduling",), dependency_hints=("runtime_job_queue", "runtime_worker_pool")),
    _DiscoveryHint("runtime_worker_pool", "Runtime Worker Pool", "runtime", "Worker inventory derived from agent capabilities.", "runtime_foundation", ("app/platform/runtime/worker_pool.py",), declared_capabilities=("worker_pool",), dependency_hints=("agent_manifest_registry",), overlap_hints=("agent_worker",)),
    _DiscoveryHint("platform_event_bus", "Platform Event Bus", "events", "Platform event contracts and dispatch declarations.", "event_observation", ("app/platform/events/event.py", "app/platform/events/event_bus.py", "app/platform/events/event_dispatcher.py"), ("PlatformEvent", "record_event", "dispatch_event"), ("event_contract", "event_dispatch"), overlap_hints=("data_event_store",)),
    _DiscoveryHint("data_event_store", "Data Event Store", "events", "Data-event model and store.", "data_foundation", ("app/platform/data/events/event_store.py", "app/platform/data/events/event_models.py"), declared_capabilities=("event_storage",), overlap_hints=("platform_event_bus",)),
    _DiscoveryHint("pubsub", "GCP Pub/Sub", "infrastructure", "Candidate managed event transport.", "gcp_infrastructure", ("infra/terraform/modules/pubsub/README.md",), declared_capabilities=("managed_event_transport",), dependency_hints=("platform_event_bus",), production_configuration_paths=("infra/terraform/modules/pubsub",)),
    _DiscoveryHint("repository_intelligence", "Repository Intelligence", "repository", "Bounded repository maps and verified source evidence.", "repository_intelligence", ("app/platform/repository_intelligence/service.py",), ("inspect_repository_evidence", "build_repository_context", "build_file_plan"), ("repository_evidence", "path_fingerprint")),
    _DiscoveryHint("sandbox_workspace_materialization", "Local Sandbox Workspace Materialization", "sandbox", "Approval-gated materialization of generated static-preview files inside a guarded local workspace.", "application_runtime", ("app/platform/services/materialization_sandbox_writer_service.py", "app/platform/services/materialization_execution_gate_service.py"), ("write_generated_file_to_local_sandbox", "execute_approved_materialization"), ("sandbox_materialization", "isolated_workspace"), ("materialization_approval",), ("materialization_dry_run",)),
    _DiscoveryHint("manual_browser_test_harness", "Manual Browser Test Harness", "sandbox", "Prepares browser inspection evidence for sandbox-materialized static application files without starting generated code.", "application_validation", ("app/platform/services/manual_browser_test_harness_service.py",), ("prepare_manual_browser_test_harness",), ("browser_harness", "static_preview_validation"), ("sandbox_workspace_materialization",)),
    _DiscoveryHint("runtime_readiness_detector", "Runtime Readiness Detector", "sandbox", "Inspects generated application files and reports runtime prerequisites, entry points, commands, and approval requirements.", "application_runtime", ("app/platform/services/runtime_readiness_detector_service/part_1.py", "app/platform/services/runtime_readiness_detector_service/part_2.py", "app/platform/services/runtime_readiness_detector_service/part_3.py"), ("detect_runtime_readiness_for_workflow", "detect_runtime_readiness_for_generated_file", "detect_runtime_readiness_from_files"), ("runtime_readiness", "pre_production_inspection")),
    _DiscoveryHint("runtime_run_plan", "Runtime Run Plan", "sandbox", "Builds a no-execution run plan from generated-application readiness evidence.", "application_runtime", ("app/platform/services/runtime_run_plan_builder_service.py",), ("build_runtime_run_plan_from_readiness", "build_runtime_run_plan_for_workflow"), ("runtime_run_planning", "pre_production_plan"), ("runtime_readiness_detector",)),
    _DiscoveryHint("runtime_approval_gate", "Runtime Approval Gate", "sandbox", "Persists approval or rejection records for a generated-application runtime plan without starting execution.", "application_governance", ("app/platform/services/runtime_approval_gate_service/part_1.py", "app/platform/services/runtime_approval_gate_service/part_2.py", "app/platform/services/runtime_approval_gate_service/part_3.py", "app/platform/persistence/model_definitions/materialization.py"), ("approve_runtime_run_plan_for_workflow", "reject_runtime_run_plan_for_workflow", "get_latest_runtime_approval_for_workflow"), ("runtime_approval", "approval_record"), ("runtime_run_plan", "persistence")),
    _DiscoveryHint("controlled_sandbox_runtime", "Controlled Sandbox Runtime", "sandbox", "Starts and stops an approved generated application inside the guarded local sandbox boundary.", "application_runtime", ("app/platform/services/controlled_sandbox_runtime_service.py", "app/platform/services/controlled_runtime_runner.py", "app/platform/services/controlled_runtime_status.py", "app/platform/services/controlled_runtime_workspace.py", "app/platform/services/controlled_runtime_safety.py"), ("start_controlled_sandbox_runtime_for_workflow", "get_controlled_sandbox_runtime_status", "stop_controlled_sandbox_runtime"), ("controlled_execution", "isolated_execution", "pre_production_runtime"), ("runtime_readiness_detector", "runtime_run_plan", "runtime_approval_gate", "sandbox_workspace_materialization"), ("hosted_sandbox_boundary",)),
    _DiscoveryHint("runtime_log_capture", "Controlled Runtime Log Capture", "sandbox", "Captures bounded stdout, stderr, process status, and exit evidence from controlled sandbox execution.", "application_observability", ("app/platform/services/controlled_runtime_logs.py",), ("init_runtime_log_record", "start_runtime_log_readers", "runtime_log_snapshot"), ("runtime_logs", "runtime_observation"), ("controlled_sandbox_runtime",)),
    _DiscoveryHint("runtime_failure_analysis", "Runtime Failure Analysis", "sandbox", "Classifies controlled-runtime log evidence without mutating generated applications.", "application_repair", ("app/platform/services/runtime_failure_analyzer_service.py",), ("analyze_runtime_failure_from_logs", "analyze_runtime_failure_for_workflow"), ("failure_analysis", "behavioural_evidence"), ("runtime_log_capture",)),
    _DiscoveryHint("hosted_sandbox_boundary", "Hosted Sandbox Boundary", "sandbox", "Inspects hosted-sandbox eligibility through a contract-only boundary without starting hosted infrastructure.", "application_runtime", ("app/platform/services/hosted_sandbox_boundary_service.py",), ("inspect_hosted_sandbox_boundary",), ("hosted_sandbox_contract", "environment_boundary"), ("runtime_run_plan", "sandbox_workspace_materialization"), ("controlled_sandbox_runtime",)),
    _DiscoveryHint("materialization_dry_run", "Workspace Materialization Dry Run", "simulation", "Models guarded workspace file writes without writing files or starting generated code.", "application_validation", ("app/platform/services/materialization_dry_run_service.py",), ("build_materialization_dry_run",), ("dry_run", "materialization_simulation", "what_if_analysis"), overlap_hints=("sandbox_workspace_materialization",)),
    _DiscoveryHint("workflow_step_simulation", "Agent Workflow Step Simulation", "simulation", "Produces deterministic safe-mode workflow-step results without invoking specialist handlers.", "workflow_runtime", ("app/platform/services/agent_workflow_steps.py", "app/platform/services/agent_workflow_executor_service.py"), ("complete_step_simulation",), ("workflow_simulation", "behavioural_rehearsal")),
    _DiscoveryHint("restore_impact_simulation", "Generated File Restore Simulation", "simulation", "Builds a dry-run impact report for restoring a generated-file version before mutation.", "application_lifecycle", ("app/platform/services/generated_file_version_restore_simulation_service.py",), ("simulate_generated_file_version_restore",), ("restore_simulation", "impact_analysis", "what_if_analysis")),
    _DiscoveryHint("repair_failure_simulation", "Repair Failure Simulation", "simulation", "Creates controlled generated-application drift scenarios inside a temporary sandbox for repair-loop validation.", "repair", ("app/platform/repair/simulate_failure/part_1.py", "app/platform/repair/simulate_failure/part_2.py"), ("run_simulation",), ("failure_simulation", "behavioural_rehearsal", "temporary_sandbox"), ("runtime_failure_analysis",)),
)


def get_capability_intelligence_status() -> dict[str, Any]:
    records = _aggregate_records()
    return {
        "status": "capability-intelligence-ready",
        "mode": "read-only-evidence-derived-aggregator",
        "record_count": len(records),
        "sources": _source_summary(),
        "lifecycle_semantics": dict(LIFECYCLE_SEMANTICS),
        "integration_semantics": dict(INTEGRATION_SEMANTICS),
        "production_semantics": dict(PRODUCTION_SEMANTICS),
        "classification_rules": {
            "placeholder": "deferred declaration evidence and no material implementation",
            "foundation": "material implementation without canonical execution-path evidence",
            "integrated": "material implementation with canonical execution-path evidence",
            "production_active": "capability-specific activation evidence required",
        },
        "mutation_enabled": False,
    }


def discover_relevant_capabilities(
    objective: str,
    approved_plan: Any = None,
    affected_domains: Iterable[str] | None = None,
    affected_paths: Iterable[str] | None = None,
    *,
    limit: int = 16,
) -> dict[str, Any]:
    query = _query_text(objective, approved_plan, affected_domains, affected_paths)
    paths = tuple(str(path).strip() for path in (affected_paths or ()) if str(path).strip())
    scored = [(_relevance_score(record, query, affected_domains or (), paths), record) for record in _aggregate_records()]
    selected = [record for score, record in sorted(scored, key=lambda item: (-item[0], item[1].capability_id)) if score > 0]
    return _context_response(selected[: max(1, min(limit, 30))], objective, query)


def get_capability_context(capability_ids: Iterable[str]) -> dict[str, Any]:
    requested = {str(value).strip() for value in capability_ids if str(value).strip()}
    selected = [record for record in _aggregate_records() if record.capability_id in requested]
    return _context_response(selected, "Capability context lookup", " ".join(sorted(requested)))


def _aggregate_records() -> list[CapabilityRecord]:
    reference_index = _build_reference_index()
    records = [_derive_hint_record(hint, reference_index) for hint in _SYSTEM_DISCOVERY_HINTS]
    records.extend(_declared_source_records(reference_index))
    unique = {record.capability_id: record for record in records}
    return [unique[key] for key in sorted(unique)]


def _derive_hint_record(hint: _DiscoveryHint, reference_index: dict[str, Any]) -> CapabilityRecord:
    inspected = inspect_repository_evidence(list(hint.candidate_paths), requested_by=f"capability-intelligence:{hint.capability_id}")
    contexts = {item["path"]: item for item in inspected.get("context", [])}
    implementation: list[EvidenceItem] = []
    declarations: list[EvidenceItem] = []
    source_paths: list[str] = []
    for manifest in inspected.get("manifest", []):
        path = str(manifest["path"])
        source_paths.append(path)
        content = str(contexts.get(path, {}).get("content") or "")
        fingerprint = str(manifest.get("fingerprint") or "") or None
        if _is_deferred_declaration(path, content):
            declarations.append(_evidence("DECLARATION", path, "A deferred or declaration-only artifact exists.", fingerprint, "HIGH"))
        elif _is_material_implementation(path, content):
            implementation.append(_evidence("IMPLEMENTATION", path, "A material implementation source exists.", fingerprint, "HIGH"))
        else:
            declarations.append(_evidence("DECLARATION", path, "A capability-related source artifact exists; material implementation is unproven.", fingerprint, "MEDIUM"))

    consumers, execution = _reference_evidence(hint, source_paths, reference_index)
    dependencies = tuple(
        _evidence("DECLARED_DEPENDENCY_HINT", f"discovery-hint:{hint.capability_id}", f"Potential dependency: {dependency}.", None, "LOW")
        for dependency in hint.dependency_hints
    )
    overlaps = tuple(
        _evidence("DECLARED_OVERLAP_HINT", f"discovery-hint:{hint.capability_id}", f"Potentially overlapping responsibility with {other}; architecture decision not made.", None, "LOW")
        for other in hint.overlap_hints
    )
    if implementation:
        overlaps += tuple(
            _evidence("EVIDENCED_OVERLAP_SIGNAL", f"repository:{source_paths[0]}", f"Both {hint.capability_id} and {other} have candidate implementation evidence for related declared semantics.", implementation[0].fingerprint, "MEDIUM")
            for other in hint.overlap_hints
            if _hint_has_implementation(other)
        )

    production_config = _production_evidence(hint.production_configuration_paths, "PRODUCTION_CONFIGURATION")
    production_active = _production_evidence(hint.production_activation_paths, "PRODUCTION_ACTIVATION")
    lifecycle, integration, production, unknowns, confidence = _derive_statuses(
        implementation, declarations, consumers, execution, production_config, production_active, reference_index
    )
    evidence_payload = {
        "implementation": implementation,
        "declarations": declarations,
        "consumers": consumers,
        "dependencies": dependencies,
        "execution": execution,
        "production_configuration": production_config,
        "production_activation": production_active,
        "overlaps": overlaps,
        "scope": reference_index["scope"],
    }
    return CapabilityRecord(
        hint.capability_id, hint.canonical_name, hint.domain_hint, hint.purpose_hint, hint.owning_layer_hint,
        lifecycle, integration, production, hint.candidate_interfaces, hint.declared_capabilities,
        tuple(source_paths), tuple(implementation), tuple(declarations), tuple(consumers), dependencies,
        tuple(execution), tuple(execution), tuple(production_config), tuple(production_active), overlaps,
        dict(reference_index["scope"]), tuple(unknowns), _fingerprint(evidence_payload), confidence,
    )


def _declared_source_records(reference_index: dict[str, Any]) -> list[CapabilityRecord]:
    declarations: list[tuple[str, str, str, tuple[str, ...], str, str]] = []
    for resource in base_registry().values():
        declarations.append((f"unified_registry_{resource.resource_id}", resource.name, resource.resource_type, (str(resource.metadata.get("capability") or ""),), "app/platform/registry/registry.py", f"registry-resource:{resource.resource_id}"))
    for manifest in all_manifests().values():
        declarations.append((f"agent_manifest_{manifest.agent_id}", f"Agent Manifest: {manifest.agent_id}", manifest.department, tuple(manifest.capabilities), "app/platform/agents/manifest_registry.py", f"agent-manifest:{manifest.agent_id}"))
    for agent in list_agents():
        declarations.append((f"agent_registry_{agent['agent_id']}", f"Registered Agent: {agent['name']}", "agents", tuple(agent.get("capabilities") or ()), "app/platform/agents/registry.py", f"runtime-agent:{agent['agent_id']}"))
    for plugin in plugin_registry().values():
        declarations.append((f"plugin_{plugin.plugin_id}", f"Plugin: {plugin.plugin_id}", "plugins", tuple(plugin.capabilities), "app/platform/plugins/plugin_registry.py", f"plugin:{plugin.plugin_id}@{plugin.version}"))
    for provider_id, capabilities in provider_registry().items():
        declarations.append((f"provider_{provider_id}", f"Provider: {provider_id}", "providers", tuple(capabilities), "app/platform/plugins/provider_registry.py", f"provider:{provider_id}"))
    for event_type in event_registry():
        declarations.append((f"event_type_{event_type.replace('.', '_')}", f"Event Type: {event_type}", "events", (event_type,), "app/platform/events/event_registry.py", f"event-type:{event_type}"))
    return [_declaration_record(*item, reference_index=reference_index) for item in declarations]


def _declaration_record(capability_id: str, name: str, domain: str, capabilities: tuple[str, ...], path: str, reference: str, *, reference_index: dict[str, Any]) -> CapabilityRecord:
    inspected = inspect_repository_evidence([path], requested_by=f"capability-intelligence:{capability_id}")
    manifest = (inspected.get("manifest") or [{}])[0]
    fingerprint = str(manifest.get("fingerprint") or "") or None
    declaration = _evidence("DECLARATION", reference, "An authoritative registry declaration exists.", fingerprint, "HIGH")
    evidence_fingerprint = _fingerprint({"declaration": declaration, "path": path})
    return CapabilityRecord(
        capability_id=capability_id,
        canonical_name=name,
        domain=domain,
        purpose="Declared capability from an existing authoritative registry.",
        owning_layer="distributed_registry",
        lifecycle_classification="UNKNOWN",
        integration_status="UNKNOWN",
        production_status="PRODUCTION_UNPROVEN",
        declared_interfaces=(),
        declared_capabilities=capabilities,
        source_paths=(path,) if fingerprint else (),
        implementation_evidence=(),
        declaration_evidence=(declaration,),
        consumer_evidence=(),
        dependency_evidence=(),
        integration_evidence=(),
        execution_path_evidence=(),
        production_configuration_evidence=(),
        production_activation_evidence=(),
        overlap_evidence=(),
        inspection_scope=dict(reference_index["scope"]),
        unknowns=("Registry declaration does not prove implementation, integration, or production activation.",),
        evidence_fingerprint=evidence_fingerprint,
        confidence="MEDIUM",
    )


def _build_reference_index() -> dict[str, Any]:
    candidates = sorted(path for path in (REPO_ROOT / "app/platform").rglob("*.py") if "__pycache__" not in path.parts)
    selected = candidates[:MAX_REFERENCE_FILES]
    entries: list[dict[str, Any]] = []
    for path in selected:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if len(content) > MAX_REFERENCE_FILE_CHARS:
            content = content[:MAX_REFERENCE_FILE_CHARS]
        relative = path.relative_to(REPO_ROOT).as_posix()
        entries.append({"path": relative, "content": content, "fingerprint": hashlib.sha256(content.encode()).hexdigest()})
    return {
        "entries": entries,
        "scope": {
            "root": "app/platform",
            "candidate_file_count": len(candidates),
            "inspected_file_count": len(entries),
            "max_files": MAX_REFERENCE_FILES,
            "complete_within_root": len(entries) == len(candidates),
            "excluded": "non-Python files, __pycache__, files beyond bounded limit, and unreadable files",
        },
    }


def _reference_evidence(hint: _DiscoveryHint, own_paths: list[str], index: dict[str, Any]) -> tuple[list[EvidenceItem], list[EvidenceItem]]:
    module_references = tuple(path[:-3].replace("/", ".") for path in own_paths if path.endswith(".py"))
    needles = tuple(value for value in (*module_references, *hint.candidate_interfaces) if len(value) >= 5)
    consumers: list[EvidenceItem] = []
    execution: list[EvidenceItem] = []
    for entry in index["entries"]:
        path = entry["path"]
        if path in own_paths or _is_check_path(path):
            continue
        matches = [needle for needle in needles if needle in entry["content"]]
        if not matches:
            continue
        fact = f"References declared interface/module: {', '.join(sorted(matches)[:3])}."
        item = _evidence("CONSUMER_REFERENCE", path, fact, entry["fingerprint"], "HIGH")
        consumers.append(item)
        if _is_canonical_execution_path(path):
            execution.append(_evidence("EXECUTION_PATH_REFERENCE", path, fact, entry["fingerprint"], "HIGH"))
        if len(consumers) >= 12:
            break
    return consumers, execution


def _derive_statuses(implementation: list[EvidenceItem], declarations: list[EvidenceItem], consumers: list[EvidenceItem], execution: list[EvidenceItem], production_config: list[EvidenceItem], production_active: list[EvidenceItem], index: dict[str, Any]) -> tuple[str, str, str, list[str], str]:
    complete = bool(index["scope"]["complete_within_root"])
    placeholder = bool(declarations) and not implementation and any("deferred" in item.fact.lower() for item in declarations)
    if placeholder:
        lifecycle, integration = "PLACEHOLDER", "PLACEHOLDER"
    elif implementation and execution:
        lifecycle, integration = "INTEGRATED", "INTEGRATED"
    elif implementation:
        lifecycle = "FOUNDATION"
        integration = "IMPLEMENTED" if consumers else ("DISCONNECTED" if complete else "UNKNOWN")
    else:
        lifecycle, integration = "UNKNOWN", "UNKNOWN"
    production = "PRODUCTION_ACTIVE" if production_active else ("PRODUCTION_CONFIGURED" if production_config else "PRODUCTION_UNPROVEN")
    unknowns: list[str] = []
    if not complete:
        unknowns.append("Consumer scan was bounded and incomplete; absence of references is not global non-use evidence.")
    if not production_active:
        unknowns.append("Production activation is not proven by the inspected capability-specific evidence.")
    if not execution:
        unknowns.append("No canonical execution-path reference was evidenced in the inspected scope.")
    confidence = "HIGH" if implementation and complete else ("MEDIUM" if implementation or declarations else "LOW")
    return lifecycle, integration, production, unknowns, confidence


def _production_evidence(paths: Iterable[str], evidence_type: str) -> list[EvidenceItem]:
    result: list[EvidenceItem] = []
    for raw_path in paths:
        path = REPO_ROOT / raw_path
        files = [path] if path.is_file() else sorted(path.rglob("*"))[:20] if path.is_dir() else []
        for file_path in files:
            if not file_path.is_file() or file_path.name.lower() in {"readme.md", "readme"}:
                continue
            try:
                content = file_path.read_bytes()
            except OSError:
                continue
            result.append(_evidence(evidence_type, file_path.relative_to(REPO_ROOT).as_posix(), "Capability-specific production artifact exists.", hashlib.sha256(content).hexdigest(), "MEDIUM"))
    return result


def _is_material_implementation(path: str, content: str) -> bool:
    if not path.endswith(".py"):
        return False
    substantive = [line for line in content.splitlines() if line.strip() and not line.lstrip().startswith(("#", '"""', "'''"))]
    return len(substantive) >= 4 and any(token in content for token in ("def ", "class ", "@dataclass"))


def _is_deferred_declaration(path: str, content: str) -> bool:
    if not path.lower().endswith(("readme", "readme.md", ".md")):
        return False
    lowered = content.lower()
    return any(token in lowered for token in ("will be added", "deferred", "placeholder", "future"))


def _is_check_path(path: str) -> bool:
    return path.endswith("_check.py") or "/checks/" in path or "_check/" in path


def _is_canonical_execution_path(path: str) -> bool:
    return path == "app/platform/server.py" or any(
        marker in path for marker in ("/api/", "/operating_console/", "/agents/worker.py", "/services/agent_workflow_executor_service")
    )


def _hint_has_implementation(capability_id: str) -> bool:
    hint = next((item for item in _SYSTEM_DISCOVERY_HINTS if item.capability_id == capability_id), None)
    if not hint:
        return False
    inspected = inspect_repository_evidence(list(hint.candidate_paths), requested_by="capability-intelligence:overlap")
    contexts = {item["path"]: str(item.get("content") or "") for item in inspected.get("context", [])}
    return any(_is_material_implementation(path, content) for path, content in contexts.items())


def _evidence(evidence_type: str, source: str, fact: str, fingerprint: str | None, confidence: str) -> EvidenceItem:
    return EvidenceItem(evidence_type, source, fact, fingerprint, confidence)


def _query_text(objective: str, plan: Any, domains: Iterable[str] | None, paths: Iterable[str] | None) -> str:
    parts = [objective, json.dumps(plan, sort_keys=True, default=str) if plan is not None else ""]
    parts.extend(sorted(str(item) for item in (domains or ())))
    parts.extend(sorted(str(item) for item in (paths or ())))
    return " ".join(parts).lower()


def _relevance_score(record: CapabilityRecord, query: str, domains: Iterable[str], paths: tuple[str, ...]) -> int:
    if record.capability_id.startswith("event_type_"):
        event_name = record.declared_capabilities[0].lower() if record.declared_capabilities else ""
        if event_name not in query and event_name.replace(".", " ") not in query:
            return 0
    domain_set = {str(item).lower().strip() for item in domains}
    score = 4 if record.domain.lower() in domain_set or record.owning_layer.lower() in domain_set else 0
    terms = _tokens(query)
    record_terms = _tokens(" ".join((record.capability_id, record.canonical_name, record.domain, record.purpose, record.owning_layer, *record.declared_interfaces, *record.declared_capabilities, *record.source_paths)))
    score += len(terms & record_terms)
    for path in paths:
        normalized = path.rstrip("/")
        explicit_directory = path.endswith("/") or (REPO_ROOT / normalized).is_dir()
        if any(normalized == source or (explicit_directory and source.startswith(normalized + "/")) for source in record.source_paths):
            score += 6
    return score


def _tokens(value: str) -> set[str]:
    normalized = "".join(character if character.isalnum() else " " for character in value.lower())
    stop = {"a", "an", "and", "agent", "capabilities", "capability", "for", "from", "in", "is", "make", "of", "platform", "service", "task", "the", "to", "with"}
    return {token for token in normalized.split() if len(token) > 2 and token not in stop}


def _context_response(records: list[CapabilityRecord], objective: str, query: str) -> dict[str, Any]:
    serialized = [asdict(record) for record in sorted(records, key=lambda item: item.capability_id)]
    stable_evidence = {"source_revision": _source_revision(), "objective": objective.strip(), "query_fingerprint": _fingerprint(query), "capabilities": serialized}
    context_fingerprint = _fingerprint(stable_evidence)
    return {
        "status": "capability-context-ready",
        "capability_context_id": f"CAPCTX-{context_fingerprint[:12].upper()}",
        "source_revision": stable_evidence["source_revision"],
        "context_fingerprint": context_fingerprint,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bounded": True,
        "read_only": True,
        "capability_count": len(serialized),
        "capabilities": serialized,
    }


def _source_revision() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "repository-revision-unavailable"


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _source_summary() -> dict[str, int]:
    return {
        "unified_registry": len(base_registry()), "agent_manifest_registry": len(all_manifests()),
        "agent_registry": len(list_agents()), "delegated_capabilities": len(capability_map()),
        "plugins": len(plugin_registry()), "providers": len(provider_registry()),
        "event_types": len(event_registry()), "discovery_hints": len(_SYSTEM_DISCOVERY_HINTS),
        "company_intelligence": 1, "company_brain": 1, "executive_context": 1,
        "repository_intelligence": 1,
    }
