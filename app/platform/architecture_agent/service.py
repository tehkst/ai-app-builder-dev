from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.architecture_agent.validator import validate_architecture_decision


def create_architecture_decision(payload: dict[str, Any]) -> dict[str, Any]:
    capability_context = payload.get("capability_context") if isinstance(payload.get("capability_context"), dict) else {}
    repository_evidence = payload.get("repository_evidence") if isinstance(payload.get("repository_evidence"), dict) else {}
    candidate = payload.get("candidate_artifact") if isinstance(payload.get("candidate_artifact"), dict) else None
    artifact = candidate or _generate_artifact(payload, capability_context, repository_evidence)
    validation = validate_architecture_decision(artifact, capability_context, repository_evidence)
    correction_attempted = False
    if not validation["valid"] and candidate is not None:
        correction_attempted = True
        artifact = _generate_artifact(payload, capability_context, repository_evidence)
        validation = validate_architecture_decision(artifact, capability_context, repository_evidence)
    if not validation["valid"]:
        return {
            "success": False,
            "status": "architecture-review-blocked",
            "validation_errors": validation["errors"],
            "correction_attempted": correction_attempted,
            "architecture_decision": None,
        }
    artifact["status"] = "validated"
    artifact["validation"] = validation
    return {
        "success": True,
        "status": "architecture-decision-validated",
        "correction_attempted": correction_attempted,
        "validation_errors": [],
        "architecture_decision": artifact,
    }


def _generate_artifact(payload: dict[str, Any], capability_context: dict[str, Any], repository_evidence: dict[str, Any]) -> dict[str, Any]:
    mission_id = str(payload.get("mission_id") or "")
    objective = str(payload.get("objective") or payload.get("goal") or "")
    plan = payload.get("approved_plan") if isinstance(payload.get("approved_plan"), dict) else {}
    constraints = [str(item) for item in payload.get("existing_constraints") or [] if str(item).strip()]
    required_validation = [str(item) for item in plan.get("validation_plan") or [] if str(item).strip()]
    capabilities = capability_context.get("capabilities") if isinstance(capability_context.get("capabilities"), list) else []
    decisions = [_decision_for_capability(item, mission_id, required_validation) for item in capabilities]
    decisions = [item for item in decisions if item]
    if not decisions:
        decisions = [_new_component_decision(payload, capability_context, required_validation)]
    decision_seed = {
        "mission_id": mission_id,
        "capability_context_id": capability_context.get("capability_context_id"),
        "objective": objective,
        "decisions": decisions,
    }
    artifact = {
        "decision_id": f"ARCH-{_digest(decision_seed)[:12].upper()}",
        "mission_id": mission_id,
        "capability_context_id": capability_context.get("capability_context_id"),
        "capability_context_fingerprint": capability_context.get("context_fingerprint"),
        "source_revision": capability_context.get("source_revision"),
        "objective": objective,
        "status": "pending-validation",
        "decisions": decisions,
        "architecture_summary": _architecture_summary(decisions),
        "integration_contracts": _integration_contracts(decisions),
        "architecture_constraints": constraints + [
            "Capability Intelligence evidence is observational and does not supply architecture dispositions.",
            "No repository mutation, merge, deployment, or rollback is authorized by this artifact.",
        ],
        "required_repository_evidence": [
            {"path": item.get("path"), "fingerprint": item.get("fingerprint"), "relevance": item.get("relevance")}
            for item in repository_evidence.get("manifest", [])
        ],
        "required_validation": required_validation or ["Validate affected modules and architecture integration boundaries."],
        "known_unknowns": _known_unknowns(capabilities, repository_evidence),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return artifact


def _decision_for_capability(capability: dict[str, Any], mission_id: str, validation: list[str]) -> dict[str, Any] | None:
    capability_id = str(capability.get("capability_id") or "")
    evidence = _capability_references(capability)
    if not capability_id or not evidence:
        return None
    integration = str(capability.get("integration_status") or "UNKNOWN")
    lifecycle = str(capability.get("lifecycle_classification") or "UNKNOWN")
    if integration == "INTEGRATED":
        decision = "REUSE"
        rationale = "Existing implementation and canonical execution-path evidence support using the current owner and interface."
    elif capability.get("implementation_evidence"):
        decision = "INTEGRATE"
        rationale = "Material implementation exists, but supplied evidence does not prove complete canonical execution integration."
    elif lifecycle == "PLACEHOLDER":
        return None
    else:
        return None
    return {
        "decision_id": f"ARCHD-{_digest({'mission': mission_id, 'capability': capability_id, 'decision': decision})[:10].upper()}",
        "decision": decision,
        "capability_id": capability_id,
        "capability_name": capability.get("canonical_name"),
        "rationale_summary": rationale,
        "evidence_references": evidence[:8],
        "ownership": capability.get("owning_layer") or "ownership requires confirmation",
        "interfaces": list(capability.get("declared_interfaces") or []),
        "constraints": list(capability.get("unknowns") or []),
        "required_validation": validation or [f"Validate {capability_id} integration and existing consumers."],
        "migration_implications": ["Preserve existing consumers and state ownership while applying this decision."],
        "confidence": capability.get("confidence") or "UNKNOWN",
    }


def _new_component_decision(payload: dict[str, Any], capability_context: dict[str, Any], validation: list[str]) -> dict[str, Any]:
    proposed = payload.get("proposed_component") if isinstance(payload.get("proposed_component"), dict) else {}
    evaluated = [str(item.get("capability_id")) for item in capability_context.get("capabilities", []) if item.get("capability_id")]
    context_reference = f"capability-context:{capability_context.get('capability_context_id')}"
    name = str(proposed.get("name") or "Unresolved mission capability")
    ownership = str(proposed.get("ownership") or "Architecture ownership must be assigned before implementation")
    capability_references = [
        reference
        for capability in capability_context.get("capabilities", [])
        for reference in _capability_references(capability)
    ]
    return {
        "decision_id": f"ARCHD-{_digest({'component': name, 'context': context_reference})[:10].upper()}",
        "decision": "NEW_COMPONENT_REQUIRED",
        "proposed_component": name,
        "capability_name": name,
        "rationale_summary": "The bounded capability context contains no evidenced implementation that owns the requested responsibility.",
        "evidence_references": list(dict.fromkeys([context_reference, *capability_references])),
        "capabilities_evaluated": evaluated or ["No relevant capability records were returned by the bounded CAPCTX query."],
        "reuse_insufficiency": str(proposed.get("reuse_insufficiency") or "No supplied capability exposes an evidenced reusable interface for this responsibility."),
        "extension_insufficiency": str(proposed.get("extension_insufficiency") or "No supplied capability has evidenced ownership that can coherently receive the behaviour."),
        "integration_insufficiency": str(proposed.get("integration_insufficiency") or "No supplied pair of capabilities covers the missing responsibility through integration."),
        "ownership": ownership,
        "interfaces": list(proposed.get("interfaces") or ["Define a bounded interface before implementation."]),
        "integration_contract": str(proposed.get("integration_contract") or "Connect through existing mission identity and governance boundaries without taking ownership of existing state."),
        "lifecycle_responsibility": str(proposed.get("lifecycle_responsibility") or ownership),
        "constraints": ["This exception decision does not authorize implementation."],
        "required_validation": validation or ["Validate ownership, integration contract, and absence of a reusable capability."],
        "migration_implications": list(proposed.get("migration_implications") or ["No migration is authorized until architecture review confirms affected consumers."]),
        "confidence": "MEDIUM" if evaluated else "LOW",
    }


def _capability_references(capability: dict[str, Any]) -> list[str]:
    references: list[str] = []
    for key, items in capability.items():
        if key.endswith("_evidence") and isinstance(items, (list, tuple)):
            references.extend(str(item.get("source_reference")) for item in items if item.get("source_reference"))
    return list(dict.fromkeys(references))


def _architecture_summary(decisions: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in decisions:
        value = str(item.get("decision"))
        counts[value] = counts.get(value, 0) + 1
    return "Validated architecture boundary: " + ", ".join(f"{value} {count}" for value, count in sorted(counts.items())) + "."


def _integration_contracts(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"capability_id": item.get("capability_id"), "owner": item.get("ownership"), "interfaces": item.get("interfaces"), "decision": item.get("decision")}
        for item in decisions if item.get("decision") in {"REUSE", "EXTEND", "INTEGRATE"}
    ]


def _known_unknowns(capabilities: list[dict[str, Any]], repository_evidence: dict[str, Any]) -> list[str]:
    unknowns = [str(value) for item in capabilities for value in item.get("unknowns") or []]
    if repository_evidence.get("missing"):
        unknowns.append("Some requested repository evidence was unavailable within the bounded inspection scope.")
    return list(dict.fromkeys(unknowns))


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
