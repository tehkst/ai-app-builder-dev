from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.constitution.binder import constitution_governance_summary

WORKFLOW_STAGES = [
    {"key": "discussion", "label": "Discussion", "terminal": False},
    {"key": "proposal", "label": "Proposal", "terminal": False},
    {"key": "founder_approval", "label": "Founder Approval", "terminal": False},
    {"key": "repository_audit", "label": "Repository Audit", "terminal": False},
    {"key": "implementation_plan", "label": "Implementation Plan", "terminal": False},
    {"key": "pr_creation", "label": "PR Creation", "terminal": False},
    {"key": "ci_validation", "label": "CI Validation", "terminal": False},
    {"key": "deployment", "label": "Deployment", "terminal": False},
    {"key": "knowledge_update", "label": "Knowledge Updated", "terminal": True},
]

ROADMAP_STAGES = [
    {"key": "discussion", "label": "Discussion", "terminal": False},
    {"key": "roadmap_proposal", "label": "Roadmap Proposal", "terminal": False},
    {"key": "founder_approval", "label": "Founder Roadmap Approval", "terminal": False},
    {"key": "mission_selection", "label": "Mission Selection", "terminal": False},
    {"key": "repository_audit", "label": "Repository Audit", "terminal": False},
    {"key": "implementation_plan", "label": "Implementation Plan", "terminal": False},
    {"key": "knowledge_update", "label": "Knowledge Updated", "terminal": True},
]


def build_founder_workflow_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder Workflow Engine",
        "milestone": "FWE-02",
        "status": "founder-workflow-engine-ready",
        "purpose": "Convert Board Room conversations into visible approval-gated workflow cards without bypassing Founder governance.",
        "workflow_types": ["mission", "roadmap", "review", "audit", "deployment", "incident"],
        "default_stages": WORKFLOW_STAGES,
        "roadmap_stages": ROADMAP_STAGES,
        "governance": _governance(),
        "constitution_governance": constitution_governance_summary("founder-workflow"),
        "endpoints": {
            "summary": "GET /mission-control/founder-workflows",
            "create": "POST /mission-control/founder-workflows/create",
            "advance": "POST /mission-control/founder-workflows/advance",
            "status": "POST /mission-control/founder-workflows/status",
        },
    }


def create_founder_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    founder_request = _text(payload, "message", _text(payload, "request", _text(payload, "prompt", "")))
    workflow_type = _classify_workflow(founder_request, payload)
    workflow_id = _text(payload, "workflow_id", _id("WF", now, {"request": founder_request, "type": workflow_type}))
    title = _text(payload, "title", _title_from(founder_request, workflow_type))
    current_stage = _text(payload, "current_stage", "founder_approval")
    card = _workflow_card(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        title=title,
        current_stage=current_stage,
        created_at=now,
        founder_request=founder_request,
        proposal=payload.get("proposal"),
        mission=payload.get("mission") or payload.get("mission_plan"),
        roadmap=payload.get("roadmap_proposal"),
    )
    return {
        "company": "AI Software Factory",
        "product": "Founder Workflow Engine",
        "milestone": "FWE-02",
        "status": "workflow-card-created",
        "workflow": card,
        "next_step": card["next_action"],
    }


def advance_founder_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    workflow_id = _text(payload, "workflow_id", "WF-UNSPECIFIED")
    workflow_type = _text(payload, "workflow_type", "mission")
    requested_stage = _text(payload, "target_stage", _text(payload, "stage", "founder_approval"))
    approved = _approval_present(payload)
    stage_keys = _stage_keys(workflow_type)
    if requested_stage not in stage_keys:
        return {"status": "invalid-stage", "workflow_id": workflow_id, "error": f"Unknown stage: {requested_stage}"}
    if requested_stage in {"mission_selection", "repository_audit", "implementation_plan", "pr_creation", "ci_validation", "deployment"} and not approved:
        return {
            "company": "AI Software Factory",
            "product": "Founder Workflow Engine",
            "milestone": "FWE-02",
            "status": "blocked-awaiting-founder-approval",
            "workflow_id": workflow_id,
            "requested_stage": requested_stage,
            "governance": _governance(),
            "constitution_governance": constitution_governance_summary("founder-workflow"),
            "next_step": "Founder must approve before this workflow advances into selection, planning, implementation, or deployment.",
        }
    card = _workflow_card(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        title=_text(payload, "title", "Founder workflow"),
        current_stage=requested_stage,
        created_at=_text(payload, "created_at", now),
        founder_request=_text(payload, "message", _text(payload, "request", "")),
        proposal=payload.get("proposal"),
        mission=payload.get("mission"),
        roadmap=payload.get("roadmap_proposal"),
    )
    return {"status": "workflow-advanced", "workflow": card, "next_step": card["next_action"]}


def get_founder_workflow_status(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_id = _text(payload, "workflow_id", "WF-UNSPECIFIED")
    workflow_type = _text(payload, "workflow_type", "mission")
    current_stage = _text(payload, "current_stage", _text(payload, "stage", "founder_approval"))
    card = _workflow_card(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        title=_text(payload, "title", "Founder workflow"),
        current_stage=current_stage,
        created_at=_text(payload, "created_at", _now()),
        founder_request=_text(payload, "message", _text(payload, "request", "")),
        proposal=payload.get("proposal"),
        mission=payload.get("mission"),
        roadmap=payload.get("roadmap_proposal"),
    )
    return {"status": "workflow-status-ready", "workflow": card, "next_step": card["next_action"]}


def build_workflow_from_console_result(result: dict[str, Any], request_text: str) -> dict[str, Any]:
    proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else None
    mission = result.get("mission_plan") if isinstance(result.get("mission_plan"), dict) else None
    intelligence = result.get("conversation_intelligence") if isinstance(result.get("conversation_intelligence"), dict) else {}
    roadmap = intelligence.get("roadmap_proposal") if isinstance(intelligence.get("roadmap_proposal"), dict) else None
    workflow_type = str(intelligence.get("workflow_type") or "mission")
    status = str(result.get("status") or "workflow-created")
    if status in {"workflow-planned", "workflow-started"}:
        stage = "implementation_plan"
    elif status == "workflow-approved":
        stage = "mission_selection" if workflow_type == "roadmap" else "repository_audit"
    else:
        stage = "founder_approval"
    title = _workflow_title_from_intelligence(result, intelligence, workflow_type)
    return create_founder_workflow(
        {
            "message": request_text,
            "workflow_id": str(result.get("mission_id") or "WF-UNSPECIFIED"),
            "title": title,
            "workflow_type": workflow_type,
            "current_stage": stage,
            "proposal": proposal,
            "mission": mission,
            "roadmap_proposal": roadmap,
        }
    )["workflow"]


def _workflow_card(*, workflow_id: str, workflow_type: str, title: str, current_stage: str, created_at: str, founder_request: str, proposal: Any, mission: Any, roadmap: Any = None) -> dict[str, Any]:
    stages = _stages(current_stage, workflow_type)
    return {
        "workflow_id": workflow_id,
        "workflow_type": workflow_type,
        "title": title,
        "status": _workflow_status(current_stage),
        "created_at": created_at,
        "current_stage": current_stage,
        "stages": stages,
        "founder_request": founder_request,
        "proposal_id": _nested_text(proposal, ["proposal_id", "proposal.proposal_id"]),
        "mission_id": _nested_text(mission, ["mission_id", "execution_plan.mission_id"]),
        "roadmap_mission_count": len(roadmap.get("missions", [])) if isinstance(roadmap, dict) else 0,
        "approval_meaning": _approval_meaning(workflow_type),
        "next_action": _next_action(current_stage, workflow_type),
        "allowed_actions": _allowed_actions(current_stage, workflow_type),
        "blockers": _blockers(current_stage, workflow_type),
        "governance": _governance(),
        "constitution_governance": constitution_governance_summary("founder-workflow"),
    }


def _stages(current_stage: str, workflow_type: str) -> list[dict[str, str]]:
    source = ROADMAP_STAGES if workflow_type == "roadmap" else WORKFLOW_STAGES
    keys = [stage["key"] for stage in source]
    current_index = keys.index(current_stage) if current_stage in keys else 0
    items = []
    for index, stage in enumerate(source):
        if index < current_index:
            state = "complete"
        elif index == current_index:
            state = "current"
        else:
            state = "pending"
        items.append({"key": stage["key"], "label": stage["label"], "state": state})
    return items


def _workflow_status(current_stage: str) -> str:
    if current_stage == "knowledge_update":
        return "completed"
    if current_stage in {"founder_approval", "deployment"}:
        return "waiting-founder-action"
    return "in-progress"


def _next_action(current_stage: str, workflow_type: str) -> str:
    if workflow_type == "roadmap":
        return {
            "discussion": "Generate roadmap proposal from Board Room discussion.",
            "roadmap_proposal": "Review the roadmap proposal and request Founder approval.",
            "founder_approval": "Founder should approve, edit, or reject the roadmap. Approval does not authorize implementation.",
            "mission_selection": "Founder selects the first mission to turn into an implementation workflow.",
            "repository_audit": "Run Repository Intelligence for the selected mission.",
            "implementation_plan": "Generate implementation plan for the selected mission only.",
            "knowledge_update": "Record roadmap decisions and selected mission.",
        }.get(current_stage, "Review roadmap workflow status.")
    return {
        "discussion": "Generate proposal from Board Room discussion.",
        "proposal": "Review the proposal and request Founder approval.",
        "founder_approval": "Founder should approve, edit, or reject the workflow.",
        "repository_audit": "Run Repository Intelligence and confirm affected files.",
        "implementation_plan": "Generate small PR plan and code proposal.",
        "pr_creation": "Create feature branch PR through GitHub Executor after approval.",
        "ci_validation": "Wait for CI and run repair loop if needed.",
        "deployment": "Founder approves production deployment.",
        "knowledge_update": "Record implementation decisions and lessons learned.",
    }.get(current_stage, "Review workflow status.")


def _allowed_actions(current_stage: str, workflow_type: str) -> list[str]:
    if current_stage == "founder_approval" and workflow_type == "roadmap":
        return ["approve_roadmap", "edit_roadmap", "reject"]
    if current_stage == "founder_approval":
        return ["approve_mission", "edit_proposal", "reject"]
    if current_stage == "mission_selection":
        return ["select_mission", "hold", "request_changes"]
    if current_stage == "deployment":
        return ["approve_deploy", "rollback", "hold"]
    if current_stage == "knowledge_update":
        return ["archive", "view_summary"]
    return ["continue", "hold", "request_changes"]


def _blockers(current_stage: str, workflow_type: str) -> list[str]:
    blockers = []
    if current_stage in {"founder_approval", "pr_creation", "deployment"}:
        blockers.append("Founder approval required before mutation or production change.")
    if workflow_type == "roadmap" and current_stage == "founder_approval":
        blockers.append("Roadmap approval authorizes planning only, not implementation.")
    if current_stage == "pr_creation":
        blockers.append("GitHub Executor requires configured credential before live PR creation.")
    return blockers


def _governance() -> dict[str, Any]:
    policy = constitution_governance_summary("founder-workflow")
    return {
        "founder_approval_required": True,
        "feature_branch_only": True,
        "direct_main_writes_allowed": False,
        "auto_merge_allowed": False,
        "deployment_requires_founder_review": True,
        "login_auth_untouched": True,
        "constitution_version": policy["version"],
        "constitution_hash": policy["hash"],
        "approval_policy": policy["approval_policy"],
    }


def _classify_workflow(text: str, payload: dict[str, Any]) -> str:
    explicit = str(payload.get("workflow_type") or "").strip().lower()
    if explicit:
        return explicit
    lowered = text.lower()
    if any(word in lowered for word in ["roadmap", "architectural review", "architecture review", "do not implement", "only produce"]):
        return "roadmap"
    if any(word in lowered for word in ["deploy", "production", "rollback"]):
        return "deployment"
    if any(word in lowered for word in ["audit", "review", "check"]):
        return "audit"
    return "mission"


def _approval_present(payload: dict[str, Any]) -> bool:
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    return str(payload.get("approval_status") or approval.get("status") or "").lower() == "approved"


def _title_from(text: str, workflow_type: str) -> str:
    cleaned = " ".join(text.split())[:80]
    if workflow_type == "roadmap":
        return "Roadmap: " + (cleaned or "Founder roadmap")
    return cleaned or f"{workflow_type.title()} workflow"


def _workflow_title_from_intelligence(result: dict[str, Any], intelligence: dict[str, Any], workflow_type: str) -> str:
    suggestion = intelligence.get("mission_suggestion") if isinstance(intelligence.get("mission_suggestion"), dict) else {}
    if suggestion.get("title"):
        return str(suggestion["title"])
    return _text(result, "action", "Board Room workflow").replace("-", " ").title()


def _approval_meaning(workflow_type: str) -> str:
    policy = constitution_governance_summary("founder-workflow")["approval_policy"]
    if workflow_type == "roadmap":
        return policy[1] if len(policy) > 1 else "Roadmap approval authorizes planning only, not implementation."
    if workflow_type == "deployment":
        return "Founder approval authorizes deployment workflow review only; production traffic changes require explicit deployment approval."
    return policy[0] if policy else "Founder approval is required before mutation or production change."


def _stage_keys(workflow_type: str = "mission") -> list[str]:
    source = ROADMAP_STAGES if workflow_type == "roadmap" else WORKFLOW_STAGES
    return [stage["key"] for stage in source]


def _nested_text(source: Any, paths: list[str]) -> str | None:
    if not isinstance(source, dict):
        return None
    for path in paths:
        value: Any = source
        for part in path.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if value:
            return str(value)
    return None


def _text(payload: dict[str, Any], key: str, default: str) -> str:
    value = str(payload.get(key) or default).strip()
    return value or default


def _id(prefix: str, timestamp: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
