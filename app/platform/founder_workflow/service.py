from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

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


def build_founder_workflow_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Founder Workflow Engine",
        "milestone": "FWE-01",
        "status": "founder-workflow-engine-ready",
        "purpose": "Convert Board Room conversations into visible approval-gated workflow cards without bypassing Founder governance.",
        "workflow_types": ["mission", "review", "audit", "deployment", "incident"],
        "default_stages": WORKFLOW_STAGES,
        "governance": _governance(),
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
    )
    return {
        "company": "AI Software Factory",
        "product": "Founder Workflow Engine",
        "milestone": "FWE-01",
        "status": "workflow-card-created",
        "workflow": card,
        "next_step": card["next_action"],
    }


def advance_founder_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    workflow_id = _text(payload, "workflow_id", "WF-UNSPECIFIED")
    requested_stage = _text(payload, "target_stage", _text(payload, "stage", "founder_approval"))
    approved = _approval_present(payload)
    if requested_stage not in _stage_keys():
        return {"status": "invalid-stage", "workflow_id": workflow_id, "error": f"Unknown stage: {requested_stage}"}
    if requested_stage in {"repository_audit", "implementation_plan", "pr_creation", "ci_validation", "deployment"} and not approved:
        return {
            "company": "AI Software Factory",
            "product": "Founder Workflow Engine",
            "milestone": "FWE-01",
            "status": "blocked-awaiting-founder-approval",
            "workflow_id": workflow_id,
            "requested_stage": requested_stage,
            "governance": _governance(),
            "next_step": "Founder must approve before this workflow advances into implementation planning or execution.",
        }
    card = _workflow_card(
        workflow_id=workflow_id,
        workflow_type=_text(payload, "workflow_type", "mission"),
        title=_text(payload, "title", "Founder workflow"),
        current_stage=requested_stage,
        created_at=_text(payload, "created_at", now),
        founder_request=_text(payload, "message", _text(payload, "request", "")),
        proposal=payload.get("proposal"),
        mission=payload.get("mission"),
    )
    return {"status": "workflow-advanced", "workflow": card, "next_step": card["next_action"]}


def get_founder_workflow_status(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_id = _text(payload, "workflow_id", "WF-UNSPECIFIED")
    current_stage = _text(payload, "current_stage", _text(payload, "stage", "founder_approval"))
    card = _workflow_card(
        workflow_id=workflow_id,
        workflow_type=_text(payload, "workflow_type", "mission"),
        title=_text(payload, "title", "Founder workflow"),
        current_stage=current_stage,
        created_at=_text(payload, "created_at", _now()),
        founder_request=_text(payload, "message", _text(payload, "request", "")),
        proposal=payload.get("proposal"),
        mission=payload.get("mission"),
    )
    return {"status": "workflow-status-ready", "workflow": card, "next_step": card["next_action"]}


def build_workflow_from_console_result(result: dict[str, Any], request_text: str) -> dict[str, Any]:
    proposal = result.get("proposal") if isinstance(result.get("proposal"), dict) else None
    mission = result.get("mission_plan") if isinstance(result.get("mission_plan"), dict) else None
    status = str(result.get("status") or "workflow-created")
    if status in {"workflow-planned", "workflow-started"}:
        stage = "implementation_plan"
    elif status == "workflow-approved":
        stage = "repository_audit"
    else:
        stage = "founder_approval"
    return create_founder_workflow(
        {
            "message": request_text,
            "workflow_id": str(result.get("mission_id") or "WF-UNSPECIFIED"),
            "title": _text(result, "action", "Board Room workflow").replace("-", " ").title(),
            "current_stage": stage,
            "proposal": proposal,
            "mission": mission,
        }
    )["workflow"]


def _workflow_card(*, workflow_id: str, workflow_type: str, title: str, current_stage: str, created_at: str, founder_request: str, proposal: Any, mission: Any) -> dict[str, Any]:
    stages = _stages(current_stage)
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
        "next_action": _next_action(current_stage),
        "allowed_actions": _allowed_actions(current_stage),
        "blockers": _blockers(current_stage),
        "governance": _governance(),
    }


def _stages(current_stage: str) -> list[dict[str, str]]:
    current_index = _stage_keys().index(current_stage) if current_stage in _stage_keys() else 0
    items = []
    for index, stage in enumerate(WORKFLOW_STAGES):
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


def _next_action(current_stage: str) -> str:
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


def _allowed_actions(current_stage: str) -> list[str]:
    if current_stage == "founder_approval":
        return ["approve_mission", "edit_proposal", "reject"]
    if current_stage == "deployment":
        return ["approve_deploy", "rollback", "hold"]
    if current_stage == "knowledge_update":
        return ["archive", "view_summary"]
    return ["continue", "hold", "request_changes"]


def _blockers(current_stage: str) -> list[str]:
    blockers = []
    if current_stage in {"founder_approval", "pr_creation", "deployment"}:
        blockers.append("Founder approval required before mutation or production change.")
    if current_stage == "pr_creation":
        blockers.append("GitHub Executor requires configured credential before live PR creation.")
    return blockers


def _governance() -> dict[str, Any]:
    return {
        "founder_approval_required": True,
        "feature_branch_only": True,
        "direct_main_writes_allowed": False,
        "auto_merge_allowed": False,
        "deployment_requires_founder_review": True,
        "login_auth_untouched": True,
    }


def _classify_workflow(text: str, payload: dict[str, Any]) -> str:
    explicit = str(payload.get("workflow_type") or "").strip().lower()
    if explicit:
        return explicit
    lowered = text.lower()
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
    return cleaned or f"{workflow_type.title()} workflow"


def _stage_keys() -> list[str]:
    return [stage["key"] for stage in WORKFLOW_STAGES]


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
