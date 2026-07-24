from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


CONTRACT = "software-delivery-v1"


def create_delivery_contract(
    *,
    context: dict[str, Any],
    workflow_run_id: str,
    decision_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = decision_state if isinstance(decision_state, dict) else {}
    assumptions = decision.get("assumptions") if isinstance(decision.get("assumptions"), list) else []
    confirmed = [
        _assumption_reference(item)
        for item in assumptions
        if isinstance(item, dict) and str(item.get("state") or "") == "confirmed"
    ]
    unresolved = [
        _assumption_reference(item)
        for item in assumptions
        if isinstance(item, dict) and str(item.get("state") or "open") not in {"confirmed", "rejected"}
    ]
    scope = context.get("scope") if isinstance(context.get("scope"), dict) else {}
    now = _now()
    return {
        "contract": CONTRACT,
        "version": 1,
        "project_identity": context.get("project_id"),
        "mission_identity": context.get("mission_id"),
        "workflow_run_identity": workflow_run_id,
        "conversation_identity": context.get("conversation_id"),
        "founder_objective": context.get("founder_request"),
        "accepted_decision_references": [
            value
            for value in (
                decision.get("decision_id"),
                *(item.get("event_id") for item in decision.get("selection_events") or [] if isinstance(item, dict)),
            )
            if value
        ],
        "confirmed_assumption_references": confirmed,
        "unresolved_assumptions": unresolved,
        "product_definition_reference": None,
        "target_user": _confirmed_value(assumptions, "customer"),
        "business_outcome": scope.get("objective") or context.get("founder_request"),
        "success_criteria": list(scope.get("acceptance_criteria") or []),
        "scope": list(scope.get("in_scope") or []),
        "excluded_scope": list(scope.get("out_of_scope") or []),
        "functional_requirement_references": [],
        "non_functional_requirement_references": [],
        "ux_specification_reference": None,
        "architecture_decision_references": [],
        "repository_identity": context.get("repository") or "tehkst/ai-app-builder-dev",
        "deployment_target": context.get("deployment_target"),
        "approval_state": {"mission": "approved"},
        "current_stage": "accepted",
        "completed_stages": ["accepted"],
        "blockers": [],
        "next_governed_action": None,
        "produced_artifact_references": [],
        "validation_evidence_references": [],
        "release_evidence_references": [],
        "production_verification_reference": None,
        "founder_acceptance_reference": None,
        "rollback_readiness": {"available": False, "target_revision": None},
        "created_at": now,
        "updated_at": now,
    }


def build_product_definition(
    *,
    state: dict[str, Any],
    planning: dict[str, Any],
) -> dict[str, Any]:
    contract = state["delivery_contract"]
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    plan = planning.get("plan") if isinstance(planning.get("plan"), dict) else {}
    scope = context.get("scope") if isinstance(context.get("scope"), dict) else {}
    return add_artifact(
        contract,
        artifact_type="product_definition",
        authority="planning_service",
        source_references=_source_refs(contract, planning),
        evidence_references=[],
        content={
            "problem": contract.get("founder_objective"),
            "target_user": contract.get("target_user") or "To be confirmed from founder evidence",
            "core_workflow": plan.get("scope") or scope.get("objective"),
            "value_proposition": contract.get("business_outcome"),
            "commercial_model_assumptions": [],
            "v1_scope": list(scope.get("in_scope") or []),
            "exclusions": list(scope.get("out_of_scope") or []),
            "success_criteria": list(scope.get("acceptance_criteria") or []),
            "constraints": list(scope.get("governance_boundaries") or []),
            "dependencies": list(plan.get("dependencies") or []),
            "unresolved_risks": list(plan.get("risks") or []),
        },
    )


def build_ux_specification(
    *,
    state: dict[str, Any],
    product_definition: dict[str, Any],
) -> dict[str, Any]:
    content = product_definition.get("content") if isinstance(product_definition.get("content"), dict) else {}
    return add_artifact(
        state["delivery_contract"],
        artifact_type="ux_specification",
        authority="board_room_product_intelligence",
        source_references=[product_definition["artifact_id"]],
        evidence_references=[],
        content={
            "key_screens": ["Primary workflow", "Record detail", "Create or edit flow", "Status and history"],
            "information_architecture": ["Overview", "Core records", "Workflow", "Settings"],
            "primary_workflows": [content.get("core_workflow")],
            "user_roles": [content.get("target_user")],
            "navigation": "Task-oriented navigation with the primary workflow reachable from the first screen.",
            "interaction_states": ["empty", "loading", "ready", "validation error", "system error", "success"],
            "responsive_intent": "Core workflows remain usable on mobile and desktop without horizontal overflow.",
            "accessibility_requirements": [
                "Keyboard-operable controls",
                "Programmatic labels",
                "Visible focus states",
                "Status changes announced to assistive technology",
            ],
        },
    )


def add_existing_artifact(
    *,
    state: dict[str, Any],
    artifact_type: str,
    authority: str,
    content: dict[str, Any],
    source_references: list[str],
    evidence_references: list[str] | None = None,
) -> dict[str, Any]:
    return add_artifact(
        state["delivery_contract"],
        artifact_type=artifact_type,
        authority=authority,
        content=content,
        source_references=source_references,
        evidence_references=evidence_references or [],
    )


def add_artifact(
    contract: dict[str, Any],
    *,
    artifact_type: str,
    authority: str,
    content: dict[str, Any],
    source_references: list[str],
    evidence_references: list[str],
) -> dict[str, Any]:
    artifacts = contract.setdefault("artifacts", [])
    prior = [item for item in artifacts if item.get("artifact_type") == artifact_type]
    version = len(prior) + 1
    digest = hashlib.sha256(
        json.dumps(
            {
                "workflow_run_id": contract.get("workflow_run_identity"),
                "artifact_type": artifact_type,
                "version": version,
                "sources": source_references,
                "content": content,
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()[:16].upper()
    now = _now()
    artifact = {
        "artifact_id": "DELIVERY-%s-%s" % (artifact_type.upper().replace("_", "-"), digest),
        "artifact_type": artifact_type,
        "contract": CONTRACT,
        "version": version,
        "status": "ready",
        "authoring_authority": authority,
        "mission_id": contract.get("mission_identity"),
        "workflow_run_id": contract.get("workflow_run_identity"),
        "created_at": now,
        "updated_at": now,
        "supersedes": prior[-1].get("artifact_id") if prior else None,
        "approval_state": "approved" if artifact_type == "product_definition" else "not_required",
        "source_references": list(dict.fromkeys(value for value in source_references if value)),
        "evidence_references": list(dict.fromkeys(value for value in evidence_references if value)),
        "content": content,
    }
    artifacts.append(artifact)
    contract.setdefault("produced_artifact_references", []).append(artifact["artifact_id"])
    _set_reference(contract, artifact_type, artifact["artifact_id"])
    contract["updated_at"] = now
    contract["version"] = int(contract.get("version") or 0) + 1
    return artifact


def advance_contract(
    contract: dict[str, Any],
    stage: str,
    *,
    blocker: dict[str, Any] | None = None,
    next_governed_action: dict[str, Any] | None = None,
) -> None:
    contract["current_stage"] = stage
    completed = contract.setdefault("completed_stages", [])
    if not blocker and stage not in completed:
        completed.append(stage)
    contract["blockers"] = [blocker] if blocker else []
    contract["next_governed_action"] = next_governed_action
    contract["updated_at"] = _now()
    contract["version"] = int(contract.get("version") or 0) + 1


def record_founder_acceptance(
    contract: dict[str, Any],
    *,
    decision: str,
    actor: str,
    action_id: str,
    comment: str = "",
) -> dict[str, Any]:
    existing = contract.get("founder_acceptance")
    if isinstance(existing, dict) and existing.get("action_id") == action_id:
        return existing
    record = {
        "acceptance_id": "ACCEPTANCE-%s" % hashlib.sha256(
            ("%s:%s" % (contract.get("workflow_run_identity"), action_id)).encode("utf-8")
        ).hexdigest()[:16].upper(),
        "decision": decision,
        "actor": actor,
        "action_id": action_id,
        "comment": comment[:500],
        "verification_reference": contract.get("production_verification_reference"),
        "recorded_at": _now(),
    }
    contract["founder_acceptance"] = record
    contract["founder_acceptance_reference"] = record["acceptance_id"]
    advance_contract(
        contract,
        "complete" if decision == "accepted" else "founder_acceptance",
        next_governed_action=None,
    )
    return record


def public_delivery_summary(contract: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(contract, dict):
        return None
    return {
        key: contract.get(key)
        for key in (
            "contract",
            "version",
            "project_identity",
            "mission_identity",
            "workflow_run_identity",
            "founder_objective",
            "target_user",
            "business_outcome",
            "success_criteria",
            "scope",
            "excluded_scope",
            "repository_identity",
            "deployment_target",
            "approval_state",
            "current_stage",
            "completed_stages",
            "blockers",
            "next_governed_action",
            "produced_artifact_references",
            "validation_evidence_references",
            "release_evidence_references",
            "production_verification_reference",
            "founder_acceptance_reference",
            "rollback_readiness",
        )
    } | {
        "artifacts": [
            {
                key: artifact.get(key)
                for key in (
                    "artifact_id",
                    "artifact_type",
                    "version",
                    "status",
                    "authoring_authority",
                    "approval_state",
                    "created_at",
                    "supersedes",
                )
            }
            for artifact in contract.get("artifacts") or []
            if isinstance(artifact, dict)
        ]
    }


def _set_reference(contract: dict[str, Any], artifact_type: str, artifact_id: str) -> None:
    if artifact_type == "product_definition":
        contract["product_definition_reference"] = artifact_id
    elif artifact_type == "ux_specification":
        contract["ux_specification_reference"] = artifact_id
    elif artifact_type == "architecture_decision":
        contract.setdefault("architecture_decision_references", []).append(artifact_id)
    elif artifact_type == "production_verification":
        contract["production_verification_reference"] = artifact_id


def _source_refs(contract: dict[str, Any], source: dict[str, Any]) -> list[str]:
    refs = list(contract.get("accepted_decision_references") or [])
    for key in ("plan_id", "breakdown_id", "mission_id"):
        value = source.get(key)
        if value:
            refs.append(str(value))
    return list(dict.fromkeys(refs))


def _assumption_reference(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "assumption_id": item.get("id"),
        "category": item.get("category"),
        "value": item.get("current_value"),
        "state": item.get("state") or "open",
        "decision_impact": item.get("decision_impact"),
        "confidence": item.get("confidence"),
    }


def _confirmed_value(assumptions: list[Any], category: str) -> Any:
    for item in assumptions:
        if (
            isinstance(item, dict)
            and item.get("category") == category
            and item.get("state") == "confirmed"
        ):
            return item.get("current_value")
    return None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
