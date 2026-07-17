from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.platform.engineering_manager.service import create_engineering_breakdown
from app.platform.agents.specialists import architect_agent_handler
from app.platform.capability_intelligence.service import discover_relevant_capabilities
from app.platform.code_planner.service import validate_code_proposal
from app.platform.execution.service import create_execution_mission, get_execution_mission_evidence, record_execution_mission_evidence
from app.platform.github_execution.approved_executor import APPROVAL_PHRASE, execute_approved_github_execution
from app.platform.github_execution.pr_lifecycle import get_github_pr_status
from app.platform.planning.service import generate_engineering_plan
from app.platform.repository_intelligence.service import inspect_repository_evidence


def create_mission_from_board_room(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message") or payload.get("founder_request") or "").strip()
    if not message:
        message = "Create a governed execution mission from the current Board Room discussion."

    result = create_execution_mission(
        {
            "token": payload.get("token"),
            "founder_request": message,
            "title": _title_from_message(message),
            "mission_id": payload.get("mission_id"),
            "originating_mission_id": payload.get("originating_mission_id"),
        }
    )
    if result.get("status") not in {"execution-mission-created", "execution-mission-reused"}:
        return result
    return {
        **result,
        "runtime_classification": "legacy_process_local",
        "durable_runtime_created": False,
        "message": "Legacy execution mission created without a durable workflow run.",
    }


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
        _progress(payload, "planning", "running", "Planning Agent is preparing the mission-specific plan.")
        planning = generate_engineering_plan({"token": payload.get("token"), "mission_id": mission_id, "founder_request": founder_request})
        if planning.get("status") != "engineering-plan-created" or not _same_result_mission(planning, str(mission_id), "plan"):
            _progress(payload, "planning", "blocked", "Planning did not produce valid mission-specific evidence.")
            return _blocked_workflow(mission_id, "Planning failed. Retry planning or review the planning failure.", "planning", planning)
        record_execution_mission_evidence(str(mission_id), "planning_result", planning)
    _progress(payload, "planning", "completed", "Mission-specific planning is complete.")

    architecture = existing.get("architecture_review") if isinstance(existing.get("architecture_review"), dict) else {}
    if architecture.get("mission_id") != mission_id or architecture.get("agent_id") != "architect_agent" or (architecture.get("architecture_decision") or {}).get("status") != "validated":
        approved_plan = planning.get("plan") or {}
        affected_paths = _affected_paths(approved_plan)
        affected_domains = _affected_domains(affected_paths, founder_request)
        _progress(payload, "capability_intelligence", "running", "Capability Intelligence is identifying reusable platform capabilities.")
        capability_context = discover_relevant_capabilities(
            founder_request,
            approved_plan,
            affected_domains,
            affected_paths,
        )
        _progress(payload, "capability_intelligence", "completed", "Relevant platform capability evidence was collected.")
        _progress(payload, "repository_intelligence", "running", "Repository Intelligence is inspecting approved implementation targets.")
        repository_evidence = _bounded_repository_evidence(affected_paths)
        _progress(payload, "repository_intelligence", "completed", "Bounded repository evidence was collected.")
        _progress(payload, "architecture_agent", "running", "Architecture Agent is evaluating reuse and integration boundaries.")
        architecture_result = architect_agent_handler({
            "input_payload": {
                "goal": founder_request,
                "mission_id": mission_id,
                "approved_plan": approved_plan,
                "acceptance_criteria": approved_plan.get("acceptance_criteria") or [],
                "affected_domains": affected_domains,
                "affected_paths": affected_paths,
                "capability_context": capability_context,
                "repository_evidence": repository_evidence,
                "existing_constraints": [
                    "Founder approval remains authoritative for repository mutation, merge, deployment, and rollback.",
                    "Architecture review is read-only and cannot execute implementation.",
                ],
                "progress_observer": payload.get("progress_observer"),
            }
        })
        _progress(payload, "architecture_agent", "completed" if architecture_result.get("success") else "blocked", "Architecture Agent completed its platform-aware decision." if architecture_result.get("success") else "Architecture Agent could not produce a validated decision.")
        architecture = {
            "mission_id": mission_id,
            "agent_id": architecture_result.get("agent_id"),
            "status": "architecture-reviewed" if architecture_result.get("success") else "architecture-review-failed",
            "architecture_plan": architecture_result.get("architecture_plan") or {},
            "architecture_decision": architecture_result.get("architecture_decision") or {},
            "capability_context": {
                "capability_context_id": capability_context.get("capability_context_id"),
                "context_fingerprint": capability_context.get("context_fingerprint"),
                "source_revision": capability_context.get("source_revision"),
            },
            "repository_evidence": repository_evidence,
            "validation_errors": architecture_result.get("validation_errors") or [],
        }
        if architecture["status"] != "architecture-reviewed":
            return _blocked_workflow(mission_id, "Architecture review failed. Retry from the architecture stage.", "architecture_review", architecture_result)
        record_execution_mission_evidence(str(mission_id), "architecture_review", architecture)

    evidence = get_execution_mission_evidence(str(mission_id)) or {}
    handoff = evidence.get("engineering_handoff")
    if not _same_result_mission(handoff, str(mission_id)):
        _progress(payload, "engineering_manager", "running", "Engineering Manager is preparing the mission-specific handoff.")
        handoff = create_engineering_breakdown({
            "token": payload.get("token"),
            "mission_id": mission_id,
            "planner_output": planning,
            "architecture_decision": architecture.get("architecture_decision"),
            "capability_context_id": (architecture.get("capability_context") or {}).get("capability_context_id"),
        })
        if handoff.get("status") != "engineering-breakdown-created" or not _same_result_mission(handoff, str(mission_id)):
            _progress(payload, "engineering_manager", "blocked", "Engineering Manager could not prepare the handoff.")
            return _blocked_workflow(mission_id, "Engineering handoff preparation failed. Retry from the engineering handoff stage.", "engineering_handoff", handoff)
        record_execution_mission_evidence(str(mission_id), "engineering_handoff", handoff)
    _progress(payload, "engineering_manager", "completed", "Engineering handoff is ready.")

    return {
        "mission_id": mission_id,
        "workflow_status": "engineering-handoff-prepared",
        "approval_status": "approved",
        "mission_launch_status": "reused" if launch.get("status") == "execution-mission-reused" else "launched",
        "planning_status": "reused" if planning is existing.get("planning_result") else "completed",
        "architecture_review_status": "reused" if architecture is existing.get("architecture_review") else "completed",
        "engineering_handoff_status": "reused" if handoff is evidence.get("engineering_handoff") else "prepared",
        "current_stage": "engineering_handoff_prepared",
        "next_required_action": "Authorize engineering execution.",
        "blocked_reason": None,
        "planning_result": planning,
        "architecture_review": architecture,
        "engineering_handoff": handoff,
        "governance": _workflow_governance(),
    }


def _progress(payload: dict[str, Any], stage: str, status: str, summary: str) -> None:
    observer = payload.get("progress_observer")
    if callable(observer):
        observer(stage=stage, status=status, summary=summary)


def execute_authorized_engineering_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    mission_id = str(payload.get("mission_id") or "").strip()
    mission = get_execution_mission_evidence(mission_id) or {}
    plan_result = mission.get("planning_result") if isinstance(mission.get("planning_result"), dict) else {}
    handoff = mission.get("engineering_handoff") if isinstance(mission.get("engineering_handoff"), dict) else {}
    evidence_error = _engineering_evidence_error(mission_id, mission, plan_result, handoff)
    if evidence_error:
        return _execution_blocked(mission_id or None, "engineering_handoff", evidence_error)
    authorization_error = _execution_authorization_error(payload, mission_id)
    if authorization_error:
        return _execution_blocked(mission_id, "engineering_execution_authorization", authorization_error)

    existing_execution = mission.get("repository_execution") if isinstance(mission.get("repository_execution"), dict) else {}
    if existing_execution.get("status") == "pull-request-created" and existing_execution.get("pull_request_number"):
        return _observe_existing_pr(payload, mission_id, existing_execution, reused=True)

    change_set = mission.get("executable_change_set") if isinstance(mission.get("executable_change_set"), dict) else {}
    if change_set and (change_set.get("mission_id") != mission_id or change_set.get("source_plan_id") != (plan_result.get("plan") or {}).get("plan_id") or change_set.get("engineering_breakdown_id") != handoff.get("breakdown_id")):
        return _execution_blocked(mission_id, "repository_changes", "Executable change set conflicts with approved mission evidence.", change_set)
    file_changes = payload.get("file_changes") or (change_set.get("files") if change_set.get("change_set_status") == "change_set_ready" else None) or handoff.get("file_changes") or []
    if not _valid_file_changes(file_changes):
        return _execution_blocked(mission_id, "repository_changes", "Approved mission-specific file contents are missing or invalid.")

    validation = mission.get("repository_validation") if isinstance(mission.get("repository_validation"), dict) else {}
    if validation.get("status") != "validated":
        plan = plan_result.get("plan") if isinstance(plan_result.get("plan"), dict) else {}
        validation = validate_code_proposal({
            "mission_id": mission_id,
            "approval_status": "approved",
            "patch_proposal": {
                "mission_id": mission_id,
                "proposed_changes": file_changes,
                "validation_gates": plan.get("validation_plan") or handoff.get("validation_plan") or [],
                "files_written": False,
            },
        })
        record_execution_mission_evidence(mission_id, "repository_validation", validation)
    if validation.get("status") != "validated":
        return _execution_blocked(mission_id, "validation", "Required repository validation failed or is unavailable.", validation)

    title = str((handoff.get("epic") or {}).get("title") or mission.get("title") or f"Mission {mission_id}")
    execution = execute_approved_github_execution({
        "token": payload.get("token"),
        "mission_id": mission_id,
        "title": title,
        "branch_name": str(payload.get("branch_name") or f"mission/{mission_id}"),
        "commit_message": str(payload.get("commit_message") or f"Implement approved mission {mission_id}"),
        "pr_title": str(payload.get("pr_title") or title),
        "pr_body": str(payload.get("pr_body") or "Approved engineering execution."),
        "file_changes": file_changes,
        "approved_plan": plan_result,
        "engineering_handoff": handoff,
        "live_execution": payload.get("live_execution"),
        "approval_phrase": payload.get("approval_phrase"),
    })
    record_execution_mission_evidence(mission_id, "repository_execution", execution)
    if execution.get("status") != "pull-request-created":
        failed_stage = str(execution.get("failed_stage") or "repository_execution")
        return _execution_blocked(mission_id, failed_stage, "GitHub execution did not create a pull request.", execution)
    return _observe_existing_pr(payload, mission_id, execution, reused=False)


def _affected_paths(plan: dict[str, Any]) -> list[str]:
    paths = [
        str(item.get("path") if isinstance(item, dict) else item).strip()
        for item in plan.get("affected_files") or []
    ]
    return list(dict.fromkeys(path for path in paths if path and "to be determined" not in path.lower()))[:12]


def _affected_domains(paths: list[str], objective: str) -> list[str]:
    domains = {path.split("/")[2] for path in paths if path.startswith("app/platform/") and len(path.split("/")) > 2}
    lowered = objective.lower()
    for domain, terms in {
        "runtime": ("runtime", "durable", "worker", "queue", "long-running"),
        "sandbox": ("sandbox", "isolated execution", "controlled execution", "before commissioning"),
        "simulation": ("simulation", "simulate", "digital twin", "what-if", "what if", "rehearsal", "impact before"),
        "events": ("event", "recovery", "retry"),
        "repository": ("repository", "github", "pull request"),
        "deployment": ("deploy", "production", "rollback"),
        "company": ("company", "executive", "board room"),
    }.items():
        if any(term in lowered for term in terms):
            domains.add(domain)
    return sorted(domains)


def _bounded_repository_evidence(paths: list[str]) -> dict[str, Any]:
    inspected = inspect_repository_evidence(
        paths,
        requested_by="architect_agent",
        relevance_by_path={path: "Approved planning target requiring architecture verification." for path in paths},
        max_items=12,
    )
    return {
        "status": inspected.get("status"),
        "bounded": True,
        "requested_count": inspected.get("requested_count", 0),
        "inspected_count": inspected.get("inspected_count", 0),
        "manifest": inspected.get("manifest") or [],
        "missing": inspected.get("missing") or [],
    }


def _observe_existing_pr(payload: dict[str, Any], mission_id: str, execution: dict[str, Any], *, reused: bool) -> dict[str, Any]:
    pr_number = execution.get("pull_request_number")
    lifecycle = get_github_pr_status({"token": payload.get("token"), "pr_number": pr_number, "execution_metadata": {"mission_id": mission_id}})
    record_execution_mission_evidence(mission_id, "pr_lifecycle_result", lifecycle)
    if lifecycle.get("mission_resolution_status") != "resolved" or lifecycle.get("mission_id") != mission_id:
        return _execution_blocked(mission_id, "pr_lifecycle", "Pull request identity is unresolved, ambiguous, or conflicts with the authorized mission.", {"repository_execution": execution, "pr_lifecycle": lifecycle})
    return {
        "mission_id": mission_id,
        "workflow_status": "pull-request-created-and-observed",
        "authorization_status": "authorized",
        "engineering_execution_status": "reused" if reused else "completed",
        "repository_change_status": "completed",
        "validation_status": "passed",
        "branch": execution.get("branch_name"),
        "commit_sha": execution.get("commit"),
        "push_status": "completed",
        "pr_number": pr_number,
        "pr_url": execution.get("pull_request_url"),
        "pr_status": lifecycle.get("state") or lifecycle.get("status"),
        "current_stage": "pull_request_created_or_observed",
        "next_required_action": "Review the pull request and authorize merge when ready.",
        "blocked_reason": None,
        "repository_execution": execution,
        "pr_lifecycle": lifecycle,
        "governance": {"merge": False, "deployment": False, "traffic_shift": False, "rollback": False},
    }


def _engineering_evidence_error(mission_id: str, mission: dict[str, Any], plan: dict[str, Any], handoff: dict[str, Any]) -> str | None:
    if not mission_id or mission.get("mission_id") != mission_id:
        return "Canonical active mission evidence was not found."
    if not _same_result_mission(plan, mission_id, "plan"):
        return "Approved mission-specific planning evidence is missing or contradictory."
    if not _same_result_mission(handoff, mission_id) or not handoff.get("breakdown_id"):
        return "Mission-specific engineering handoff evidence is missing or contradictory."
    return None


def _execution_authorization_error(payload: dict[str, Any], mission_id: str) -> str | None:
    status = str(payload.get("authorization_status") or "approved").strip().lower()
    if status != "approved":
        return "Engineering execution authorization is missing or rejected."
    if str(payload.get("authorization_mission_id") or mission_id).strip() != mission_id:
        return "Engineering execution authorization belongs to a different mission."
    action = str(payload.get("authorization_action") or "github_execution").strip().lower()
    if action != "github_execution":
        return "Engineering execution authorization is for a different action."
    expires_at = str(payload.get("authorization_expires_at") or "").strip()
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                return "Engineering execution authorization has expired."
        except ValueError:
            return "Engineering execution authorization expiry is invalid."
    if payload.get("live_execution") is not True or payload.get("approval_phrase") != APPROVAL_PHRASE:
        return "Existing GitHub execution authorization gates are not satisfied."
    return None


def _valid_file_changes(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, dict) and str(item.get("path") or "").strip() and isinstance(item.get("content"), str) for item in value)


def _execution_blocked(mission_id: str | None, stage: str, reason: str, evidence: Any = None) -> dict[str, Any]:
    details = evidence if isinstance(evidence, dict) else {}
    validation_status = "not-started"
    if stage == "validation":
        validation_status = "failed" if details.get("status") == "validation-failed" else "unavailable"
    repository_completed = bool(details.get("commit") or details.get("files_changed"))
    return {
        "mission_id": mission_id,
        "workflow_status": "blocked",
        "authorization_status": "blocked" if stage == "engineering_execution_authorization" else "authorized",
        "engineering_execution_status": "not-started" if stage in {"engineering_handoff", "engineering_execution_authorization"} else "blocked",
        "repository_change_status": "completed" if repository_completed else "not-started" if stage in {"engineering_handoff", "engineering_execution_authorization"} else "blocked",
        "validation_status": validation_status,
        "branch": details.get("branch_name"),
        "commit_sha": details.get("commit"),
        "push_status": details.get("push_status", "not-started"),
        "pr_number": None,
        "pr_url": None,
        "pr_status": "not-created",
        "current_stage": stage,
        "next_required_action": reason,
        "blocked_reason": reason,
        "failure_evidence": evidence,
        "governance": {"merge": False, "deployment": False, "traffic_shift": False, "rollback": False},
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
