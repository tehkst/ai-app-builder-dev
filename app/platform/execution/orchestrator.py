from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.platform.engineering_manager.service import create_engineering_breakdown
from app.platform.execution.service import create_execution_mission, get_execution_mission_evidence, record_execution_mission_evidence
from app.platform.planning.service import generate_engineering_plan


def create_mission_from_board_room(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message") or payload.get("founder_request") or "").strip()
    if not message:
        message = "Create a governed execution mission from the current Board Room discussion."

    return create_execution_mission(
        {
            "token": payload.get("token"),
            "founder_request": message,
            "title": _title_from_message(message),
            "mission_id": payload.get("mission_id"),
            "originating_mission_id": payload.get("originating_mission_id"),
        }
    )


def launch_approved_mission_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    approval_record = approval.get("approval") if isinstance(approval.get("approval"), dict) else approval
    mission_id, approval_error = _approved_mission_identity(approval, approval_record)
    if approval_error:
        return _blocked_workflow(mission_id, approval_error, "founder_approval")
    expected_mission_id = str(payload.get("mission_id") or "").strip()
    if expected_mission_id and expected_mission_id != mission_id:
        return _blocked_workflow(str(mission_id), "Founder Approval belongs to a different mission.", "founder_approval")

    founder_request = str(payload.get("founder_request") or payload.get("message") or "").strip()
    if not founder_request:
        return _blocked_workflow(mission_id, "Approved mission description is missing.", "mission_launch")

    existing = get_execution_mission_evidence(str(mission_id)) or {}
    launch = create_execution_mission({
        "token": payload.get("token"),
        "mission_id": mission_id,
        "originating_mission_id": approval.get("originating_mission_id") or approval_record.get("originating_mission_id"),
        "founder_request": founder_request,
        "title": payload.get("title") or _title_from_message(founder_request),
    })
    if launch.get("status") not in {"execution-mission-created", "execution-mission-reused"}:
        return _blocked_workflow(mission_id, "Mission launch failed.", "mission_launch", launch)

    planning = existing.get("planning_result")
    if not _same_result_mission(planning, str(mission_id), "plan"):
        planning = generate_engineering_plan({"token": payload.get("token"), "mission_id": mission_id, "founder_request": founder_request})
        if planning.get("status") != "engineering-plan-created" or not _same_result_mission(planning, str(mission_id), "plan"):
            return _blocked_workflow(mission_id, "Planning failed. Retry planning or review the planning failure.", "planning", planning)
        record_execution_mission_evidence(str(mission_id), "planning_result", planning)

    evidence = get_execution_mission_evidence(str(mission_id)) or {}
    handoff = evidence.get("engineering_handoff")
    if not _same_result_mission(handoff, str(mission_id)):
        handoff = create_engineering_breakdown({"token": payload.get("token"), "mission_id": mission_id, "planner_output": planning})
        if handoff.get("status") != "engineering-breakdown-created" or not _same_result_mission(handoff, str(mission_id)):
            return _blocked_workflow(mission_id, "Engineering handoff preparation failed. Retry from the engineering handoff stage.", "engineering_handoff", handoff)
        record_execution_mission_evidence(str(mission_id), "engineering_handoff", handoff)

    return {
        "mission_id": mission_id,
        "workflow_status": "engineering-handoff-prepared",
        "approval_status": "approved",
        "mission_launch_status": "reused" if launch.get("status") == "execution-mission-reused" else "launched",
        "planning_status": "reused" if planning is existing.get("planning_result") else "completed",
        "engineering_handoff_status": "reused" if handoff is evidence.get("engineering_handoff") else "prepared",
        "current_stage": "engineering_handoff_prepared",
        "next_required_action": "Authorize engineering execution.",
        "blocked_reason": None,
        "planning_result": planning,
        "engineering_handoff": handoff,
        "governance": _workflow_governance(),
    }


def _approved_mission_identity(approval: dict[str, Any], record: dict[str, Any]) -> tuple[str | None, str | None]:
    status = str(record.get("decision") or approval.get("decision") or "").lower()
    if status != "approved":
        return None, "Authoritative Founder Approval is missing or rejected."
    expires_at = str(record.get("expires_at") or approval.get("expires_at") or "").strip()
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                return None, "Founder Approval has expired."
        except ValueError:
            return None, "Founder Approval expiry evidence is invalid."
    candidates = {str(value).strip() for value in (approval.get("mission_id"), record.get("mission_id")) if str(value or "").strip()}
    if len(candidates) != 1:
        return None, "Founder Approval mission identity is missing or ambiguous."
    mission_id = candidates.pop()
    if not re.fullmatch(r"MISSION-[A-Za-z0-9][A-Za-z0-9-]*", mission_id):
        return mission_id, "Founder Approval did not return a canonical MISSION-* identity."
    return mission_id, None


def _same_result_mission(result: Any, mission_id: str, nested_key: str | None = None) -> bool:
    if not isinstance(result, dict):
        return False
    nested = result.get(nested_key) if nested_key and isinstance(result.get(nested_key), dict) else {}
    return str(result.get("mission_id") or nested.get("mission_id") or "") == mission_id


def _blocked_workflow(mission_id: str | None, reason: str, stage: str, evidence: Any = None) -> dict[str, Any]:
    return {
        "mission_id": mission_id,
        "workflow_status": "blocked",
        "approval_status": "approved" if stage != "founder_approval" else "blocked",
        "mission_launch_status": "blocked" if stage in {"founder_approval", "mission_launch"} else "launched",
        "planning_status": "failed" if stage == "planning" else "completed" if stage == "engineering_handoff" else "not-started",
        "engineering_handoff_status": "failed" if stage == "engineering_handoff" else "not-started",
        "current_stage": stage,
        "next_required_action": reason,
        "blocked_reason": reason,
        "failure_evidence": evidence,
        "governance": _workflow_governance(),
    }


def _workflow_governance() -> dict[str, bool]:
    return {"founder_approval_required": True, "repository_mutation": False, "branch_creation": False, "pull_request_creation": False, "merge": False, "deployment": False}


def _title_from_message(message: str) -> str:
    words = message.split()
    return " ".join(words[:10]).strip().rstrip(".") or "Execution Mission"
