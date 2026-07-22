from __future__ import annotations

from typing import Any


def build_executive_decision_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Executive Decision Center",
        "milestone": "AFOS-002",
        "status": "guided-executive-decision-ready",
        "purpose": "Select the most appropriate Board Room next action and guide it into the existing Founder Workflow Engine without forcing manual workflow selection.",
        "decision_surfaces": [
            "continue_discussion",
            "generate_roadmap",
            "create_engineering_proposal",
            "create_incident",
            "create_deployment_review",
            "save_knowledge",
            "no_action",
        ],
        "workflow_authority": "existing_founder_workflow_engine",
    }


def decide_next_action(payload: dict[str, Any]) -> dict[str, Any]:
    ci = payload.get("conversation_intelligence") if isinstance(payload.get("conversation_intelligence"), dict) else {}
    message = str(payload.get("message") or payload.get("request") or payload.get("prompt") or "").strip()
    mode_key = str(ci.get("mode_key") or "").lower()
    workflow_type = str(ci.get("workflow_type") or "").lower()
    mission_required = bool(ci.get("mission_required"))
    text = f"{message} {ci.get('mode', '')} {ci.get('recommended_next_action', '')}".lower()

    if _incident(text):
        return _decision(
            key="create_incident",
            label="Create Incident",
            kind="incident",
            reason="The conversation appears to describe a production or access problem that should be handled as an incident workflow.",
            workflow_action="create-proposal",
            workflow_type="incident",
            initial_stage="founder_approval",
            approval_scope="incident_response",
            primary=True,
            alternatives=["continue_discussion", "open_repository_audit", "save_knowledge"],
        )
    if workflow_type == "deployment" or _deployment(text):
        return _decision(
            key="create_deployment_review",
            label="Create Deployment Review",
            kind="deployment",
            reason="The request involves production deployment or traffic movement and needs explicit deployment review.",
            workflow_action="create-proposal",
            workflow_type="deployment",
            initial_stage="founder_approval",
            approval_scope="production_deployment",
            primary=True,
            alternatives=["continue_discussion", "validate_production", "hold"],
        )
    if workflow_type == "roadmap" or mode_key in {"architecture_review", "engineering_roadmap", "product"}:
        return _decision(
            key="generate_architecture_roadmap" if mode_key == "architecture_review" else "generate_roadmap",
            label="Generate Architecture Roadmap" if mode_key == "architecture_review" else "Generate Roadmap",
            kind="roadmap",
            reason="The Founder is asking for planning, review, or prioritization before implementation.",
            workflow_action="create-proposal",
            workflow_type="roadmap",
            initial_stage="roadmap_proposal",
            approval_scope="planning_only",
            primary=True,
            alternatives=["continue_discussion", "open_repository_audit", "save_knowledge"],
        )
    if workflow_type == "implementation" or mode_key in {"implementation", "bug_fix", "security_auth"} or mission_required:
        return _decision(
            key="create_engineering_proposal",
            label="Create Engineering Proposal",
            kind="implementation",
            reason="The conversation has become executable engineering work and should enter the approval workflow.",
            workflow_action="create-proposal",
            workflow_type="mission",
            initial_stage="proposal",
            approval_scope="implementation",
            primary=True,
            alternatives=["continue_discussion", "open_repository_audit", "save_knowledge"],
        )
    if mode_key in {"knowledge", "research", "strategy"} or _knowledge(text):
        return _decision(
            key="continue_discussion",
            label="Continue Discussion",
            kind="discussion",
            reason="The request is best handled as discussion, clarification, strategy, research, or knowledge before creating a workflow.",
            workflow_action=None,
            workflow_type=None,
            initial_stage=None,
            approval_scope=None,
            primary=True,
            alternatives=["save_knowledge", "create_proposal", "no_action"],
        )
    return _decision(
        key="continue_discussion",
        label="Continue Discussion",
        kind="discussion",
        reason="No execution workflow is required yet.",
        workflow_action=None,
        workflow_type=None,
        initial_stage=None,
        approval_scope=None,
        primary=True,
        alternatives=["save_knowledge", "create_proposal", "no_action"],
    )


def _decision(
    *,
    key: str,
    label: str,
    kind: str,
    reason: str,
    workflow_action: str | None,
    workflow_type: str | None,
    initial_stage: str | None,
    approval_scope: str | None,
    primary: bool,
    alternatives: list[str],
) -> dict[str, Any]:
    requires_workflow = workflow_action is not None
    guided_workflow = {
        "enabled": requires_workflow,
        "workflow_authority": "existing_founder_workflow_engine",
        "workflow_type": workflow_type,
        "initial_stage": initial_stage,
        "approval_scope": approval_scope,
        "founder_approval_required": requires_workflow,
        "implementation_authorized": False,
        "deployment_authorized": False,
    }
    if approval_scope == "planning_only":
        guided_workflow["approval_meaning"] = "Roadmap approval authorizes planning only, not implementation."
    elif approval_scope == "production_deployment":
        guided_workflow["approval_meaning"] = "Deployment requires explicit Founder approval before production mutation."
    elif approval_scope == "implementation":
        guided_workflow["approval_meaning"] = "Implementation requires Founder approval before repository mutation."
    elif approval_scope == "incident_response":
        guided_workflow["approval_meaning"] = "Incident workflow may investigate immediately but mutation remains governed."
    else:
        guided_workflow["approval_meaning"] = None

    return {
        "company": "AI Software Factory",
        "product": "Executive Decision Center",
        "milestone": "AFOS-002",
        "status": "guided-executive-decision-ready",
        "primary_action": {
            "key": key,
            "label": label,
            "kind": kind,
            "requires_workflow": requires_workflow,
            "workflow_action": workflow_action,
            "primary": primary,
        },
        "guided_workflow": guided_workflow,
        "reason": reason,
        "alternative_actions": _alternatives(alternatives),
        "ui_contract": {
            "show_static_generate_workflow": False,
            "show_primary_contextual_action": True,
            "show_secondary_actions": True,
            "show_guided_workflow_summary": requires_workflow,
        },
        "governance": {
            "decision_engine_owns_workflow": False,
            "workflow_engine": "Founder Workflow Engine",
            "duplicate_workflow_created": False,
            "duplicate_approval_model_created": False,
        },
    }


def _alternatives(keys: list[str]) -> list[dict[str, Any]]:
    labels = {
        "continue_discussion": "Continue Discussion",
        "open_repository_audit": "Open Repository Audit",
        "save_knowledge": "Save To Knowledge",
        "create_proposal": "Create Proposal",
        "validate_production": "Validate Production",
        "hold": "Hold",
        "no_action": "No Action Required",
    }
    workflow_keys = {"create_proposal", "open_repository_audit", "validate_production"}
    return [
        {
            "key": key,
            "label": labels.get(key, key.replace("_", " ").title()),
            "requires_workflow": key in workflow_keys,
        }
        for key in keys
    ]


def _incident(text: str) -> bool:
    return any(
        term in text
        for term in [
            "broken",
            "cannot login",
            "login is down",
            "production issue",
            "incident",
            "urgent",
            "500 error",
            "cannot access",
        ]
    )


def _deployment(text: str) -> bool:
    return any(term in text for term in ["deploy", "deployment", "shift traffic", "cloud run revision", "rollback"])


def _knowledge(text: str) -> bool:
    return any(term in text for term in ["explain", "clarify", "what is", "how do", "why"])
