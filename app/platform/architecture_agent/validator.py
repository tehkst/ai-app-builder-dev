from __future__ import annotations

import json
from typing import Any


ALLOWED_DECISIONS = {
    "REUSE",
    "EXTEND",
    "INTEGRATE",
    "NEW_COMPONENT_REQUIRED",
    "DEPRECATE",
    "RETIRE_AFTER_MIGRATION",
}
NEW_COMPONENT_FIELDS = {
    "capabilities_evaluated",
    "reuse_insufficiency",
    "extension_insufficiency",
    "integration_insufficiency",
    "ownership",
    "integration_contract",
    "lifecycle_responsibility",
    "required_validation",
    "migration_implications",
}


def validate_architecture_decision(
    artifact: dict[str, Any],
    capability_context: dict[str, Any],
    repository_evidence: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    mission_id = str(artifact.get("mission_id") or "")
    context_id = str(capability_context.get("capability_context_id") or "")
    context_fingerprint = str(capability_context.get("context_fingerprint") or "")
    if not mission_id.startswith("MISSION-"):
        errors.append("mission_id must preserve canonical MISSION-* identity")
    if artifact.get("capability_context_id") != context_id or not context_id.startswith("CAPCTX-"):
        errors.append("capability_context_id must match the supplied CAPCTX identity")
    if artifact.get("capability_context_fingerprint") != context_fingerprint or not context_fingerprint:
        errors.append("capability_context_fingerprint must match supplied evidence")

    capabilities = {str(item.get("capability_id")): item for item in capability_context.get("capabilities", [])}
    evidence_references = _allowed_evidence_references(capability_context, repository_evidence)
    decisions = artifact.get("decisions") if isinstance(artifact.get("decisions"), list) else []
    if not decisions:
        errors.append("at least one structured architecture decision is required")
    seen_ids: set[str] = set()
    for index, decision in enumerate(decisions):
        prefix = f"decisions[{index}]"
        decision_id = str(decision.get("decision_id") or "")
        if not decision_id or decision_id in seen_ids:
            errors.append(f"{prefix}.decision_id must be present and unique")
        seen_ids.add(decision_id)
        value = str(decision.get("decision") or "")
        if value not in ALLOWED_DECISIONS:
            errors.append(f"{prefix}.decision is not allowed")
            continue
        capability_id = str(decision.get("capability_id") or "")
        if value != "NEW_COMPONENT_REQUIRED" and capability_id not in capabilities:
            errors.append(f"{prefix}.capability_id is absent from supplied Capability Intelligence")
        supplied_references = {str(item) for item in decision.get("evidence_references") or []}
        if not supplied_references or not supplied_references <= evidence_references:
            errors.append(f"{prefix}.evidence_references must resolve against supplied evidence")
        if value == "NEW_COMPONENT_REQUIRED":
            for field in sorted(NEW_COMPONENT_FIELDS):
                if not _present(decision.get(field)):
                    errors.append(f"{prefix}.{field} is required for NEW_COMPONENT_REQUIRED")
            evaluated = {str(item) for item in decision.get("capabilities_evaluated") or []}
            if capabilities:
                missing_evaluations = set(capabilities) - evaluated
                if missing_evaluations:
                    errors.append(f"{prefix}.capabilities_evaluated omits supplied relevant capabilities: {sorted(missing_evaluations)}")
                for evaluated_id in sorted(set(capabilities) & evaluated):
                    capability_references = _capability_evidence_references(capabilities[evaluated_id])
                    if capability_references and not supplied_references.intersection(capability_references):
                        errors.append(f"{prefix}.evidence_references does not cite evaluated capability {evaluated_id}")
        if value == "DEPRECATE":
            if not _present(decision.get("replacement_capability_id")):
                errors.append(f"{prefix}.replacement_capability_id is required for DEPRECATE")
            if not _present(decision.get("migration_implications")):
                errors.append(f"{prefix}.migration_implications is required for DEPRECATE")
            if not (_present(decision.get("known_consumers")) or _present(decision.get("unknown_consumer_scope"))):
                errors.append(f"{prefix} must preserve consumer evidence or an unknown-consumer warning")
        if value == "RETIRE_AFTER_MIGRATION":
            for field in ("replacement_capability_id", "migration_implications", "zero_consumer_verification", "removal_approval_required"):
                if not _present(decision.get(field)):
                    errors.append(f"{prefix}.{field} is required for RETIRE_AFTER_MIGRATION")
            if decision.get("removal_approval_required") is not True:
                errors.append(f"{prefix}.removal_approval_required must be true")
        if decision.get("remove_now") is True or value == "REMOVE":
            errors.append(f"{prefix} cannot directly remove a capability")

    serialized = json.dumps(artifact, sort_keys=True, default=str)
    for forbidden in ('"content":', "chain_of_thought", "reasoning_trace", "private_reasoning"):
        if forbidden in serialized:
            errors.append(f"architecture artifact contains forbidden unrestricted reasoning/source field: {forbidden}")
    return {"valid": not errors, "errors": errors, "decision_count": len(decisions)}


def _allowed_evidence_references(capability_context: dict[str, Any], repository_evidence: dict[str, Any]) -> set[str]:
    references = {f"capability-context:{capability_context.get('capability_context_id')}"}
    for capability in capability_context.get("capabilities", []):
        for key, value in capability.items():
            if key.endswith("_evidence") and isinstance(value, (list, tuple)):
                references.update(str(item.get("source_reference")) for item in value if item.get("source_reference"))
    for item in repository_evidence.get("manifest", []):
        path = str(item.get("path") or "")
        fingerprint = str(item.get("fingerprint") or "")
        if path:
            references.add(path)
            if fingerprint:
                references.add(f"repository:{path}#{fingerprint[:12]}")
    return references


def _capability_evidence_references(capability: dict[str, Any]) -> set[str]:
    references: set[str] = set()
    for key, value in capability.items():
        if key.endswith("_evidence") and isinstance(value, (list, tuple)):
            references.update(str(item.get("source_reference")) for item in value if item.get("source_reference"))
    return references


def _present(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return value is not None and value is not False
