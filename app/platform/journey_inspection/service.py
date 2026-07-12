from __future__ import annotations

import re
from typing import Any, Callable

from app.platform.board_room.service import build_board_room_summary
from app.platform.deployment.approved_cloud_run import build_cloud_run_deployment_summary
from app.platform.deployment.production_verification import build_production_verification_summary
from app.platform.engineering_manager.service import build_engineering_manager_summary
from app.platform.execution.service import build_execution_summary
from app.platform.founder_approval.service import build_founder_approval_summary
from app.platform.founder_workflow.service import build_founder_workflow_summary
from app.platform.github_execution.approved_executor import build_approved_github_execution_summary
from app.platform.github_execution.approved_merge import build_github_merge_summary
from app.platform.github_execution.pr_lifecycle import build_github_pr_summary
from app.platform.mission_execution.service import build_mission_execution_summary
from app.platform.planning.service import build_planning_summary


STAGE_DEFINITIONS = [
    ("founder_request", "Founder request"),
    ("executive_recommendation", "Executive recommendation"),
    ("founder_approval", "Founder approval"),
    ("mission_creation", "Mission creation"),
    ("planning", "Planning"),
    ("engineering_execution", "Engineering execution"),
    ("code_changes", "Code changes"),
    ("pull_request", "Pull request"),
    ("merge_approval", "Merge approval"),
    ("merge", "Merge"),
    ("deployment_approval", "Deployment approval"),
    ("production_deployment", "Production deployment"),
    ("verification", "Verification"),
    ("mission_completion", "Mission completion"),
]
STAGE_STATUSES = {"verified", "ready", "manual", "blocked", "unknown"}
TRANSITION_STATUSES = {"verified", "manual", "blocked", "unknown"}


def inspect_mission_journey(
    mission_id: str | None = None,
    *,
    source_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute a mission journey from existing evidence without mutating sources."""

    sources = _collect_sources()
    if source_overrides:
        sources.update(source_overrides)
    resolution = _resolve_mission(mission_id, sources)
    selected_mission_id = resolution["mission_id"]
    stages = _build_stages(selected_mission_id, sources)
    transitions = _build_transitions(selected_mission_id, stages, sources, resolution)
    inspectable = resolution["status"] == "resolved"
    first_break = (
        next((item for item in transitions if item["status"] != "verified"), None)
        if inspectable
        else None
    )
    missing_linkages = _missing_linkages(
        selected_mission_id,
        stages,
        transitions,
        sources,
    )
    verified_stages = sum(item["status"] == "verified" for item in stages)
    verified_transitions = sum(item["status"] == "verified" for item in transitions)
    health = _journey_health(stages, transitions) if inspectable else "blocked_for_inspection"
    reuse = _reuse_recommendations(sources)
    improvement = _smallest_improvement(first_break, resolution)
    return {
        "status": "journey-inspection-ready",
        "mode": "read-only-derived-evidence",
        "mission_id": selected_mission_id,
        "mission_resolution": resolution,
        "journey_health": health,
        "stages": stages,
        "transitions": transitions,
        "verified_stage_count": verified_stages,
        "total_stage_count": len(stages),
        "verified_transition_count": verified_transitions,
        "total_transition_count": len(transitions),
        "first_broken_or_manual_transition": first_break,
        "missing_linkages": missing_linkages,
        "reuse_recommendations": reuse,
        "smallest_next_improvement": improvement,
        "executive_summary": (
            f"Mission {selected_mission_id or 'not identified'} has {verified_stages}/{len(stages)} verified stages "
            f"and {verified_transitions}/{len(transitions)} verified transitions. "
            f"Journey health is {health}. {improvement}"
        ),
        "governance": {
            "read_only": True,
            "stores_state": False,
            "executes_work": False,
            "creates_branches": False,
            "creates_pull_requests": False,
            "merges": False,
            "deploys": False,
            "verifies_by_deploying": False,
            "rolls_back": False,
            "shifts_traffic": False,
            "mutates_approvals": False,
        },
    }


def _collect_sources() -> dict[str, dict[str, Any]]:
    builders: dict[str, Callable[[], dict[str, Any]]] = {
        "board_room": build_board_room_summary,
        "founder_approval": build_founder_approval_summary,
        "execution": build_execution_summary,
        "mission_execution": build_mission_execution_summary,
        "founder_workflow": build_founder_workflow_summary,
        "planning": build_planning_summary,
        "engineering_manager": build_engineering_manager_summary,
        "github_execution": build_approved_github_execution_summary,
        "github_pr": build_github_pr_summary,
        "github_merge": build_github_merge_summary,
        "deployment": build_cloud_run_deployment_summary,
        "verification": build_production_verification_summary,
    }
    return {name: _safe(builder) for name, builder in builders.items()}


def _safe(builder: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        result = builder()
        return result if isinstance(result, dict) else {"status": "unknown"}
    except Exception as exc:
        return {"status": "unavailable", "error": type(exc).__name__}


def _resolve_mission(
    requested: str | None,
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if requested and requested.strip():
        value = requested.strip()
        found = _source_contains_mission(sources, value)
        return {
            "status": "resolved" if found else "not_found",
            "method": "explicit_reference",
            "mission_id": value,
            "explanation": (
                "The explicitly referenced mission was found in current evidence."
                if found
                else "The explicitly referenced mission was not found in current evidence."
            ),
        }
    active = sources.get("execution", {}).get("active_mission") or {}
    value = str(active.get("mission_id") or "").strip()
    if value:
        return {
            "status": "resolved",
            "method": "current_active_mission",
            "mission_id": value,
            "explanation": "The current active execution mission supplied the canonical mission identity.",
        }
    candidates = _mission_candidates(sources)
    if candidates:
        return {
            "status": "resolved",
            "method": "most_relevant_active_mission",
            "mission_id": candidates[0],
            "explanation": "The most relevant active mission evidence supplied the canonical mission identity.",
        }
    return {
        "status": "unresolved",
        "method": "none",
        "mission_id": None,
        "explanation": "No explicit, current active, or relevant active mission identity was found.",
    }


def _source_contains_mission(
    sources: dict[str, dict[str, Any]],
    mission_id: str,
) -> bool:
    return mission_id in _mission_candidates(sources)


def _mission_candidates(sources: dict[str, dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for source in sources.values():
        if source.get("synthetic") is True:
            continue
        records = [source]
        for key in ("active_mission", "mission", "plan", "run", "workflow"):
            value = source.get(key)
            if isinstance(value, dict):
                records.append(value)
        for record in records:
            mission_id = str(record.get("mission_id") or "").strip()
            status = str(record.get("status") or "").lower()
            if mission_id and status not in {"complete", "completed", "closed"}:
                candidates.append(mission_id)
    return list(dict.fromkeys(candidates))


def _build_stages(
    mission_id: str | None,
    sources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    active = sources.get("execution", {}).get("active_mission") or {}
    same_active = bool(mission_id and active.get("mission_id") == mission_id)
    stages: list[dict[str, Any]] = []
    stages.append(_founder_request_stage(mission_id, active, same_active))
    planning_evidence = active.get("planning_result") if same_active and isinstance(active.get("planning_result"), dict) else sources["planning"]
    stages.append(_linked_or_capability_stage(
        "executive_recommendation",
        "Executive recommendation",
        mission_id,
        sources["board_room"],
        linked_keys=("recommendation", "executive_recommendation"),
        ready_statuses=("ready", "unknown"),
        source_name="Board Room",
    ))
    stages.append(_linked_or_capability_stage(
        "founder_approval",
        "Founder approval",
        mission_id,
        sources["founder_approval"],
        linked_keys=("approval_id", "approval"),
        ready_statuses=("founder-approval-ready",),
        source_name="Founder Approval",
    ))
    stages.append(_mission_creation_stage(mission_id, active, same_active))
    stages.append(_linked_or_capability_stage(
        "planning",
        "Planning",
        mission_id,
        planning_evidence.get("plan") if isinstance(planning_evidence.get("plan"), dict) else planning_evidence,
        linked_keys=("plan_id", "plan"),
        ready_statuses=("planner-ready",),
        source_name="Planning",
    ))
    engineering_evidence = active.get("engineering_handoff") if same_active and isinstance(active.get("engineering_handoff"), dict) else sources["engineering_manager"]
    stages.append(_engineering_stage(mission_id, engineering_evidence))
    stages.append(_code_change_stage(mission_id, sources["github_execution"]))
    stages.append(_pr_stage(mission_id, sources["github_pr"]))
    stages.append(_linked_or_capability_stage(
        "merge_approval",
        "Merge approval",
        mission_id,
        sources["github_merge"],
        linked_keys=("approval_id", "approval"),
        ready_statuses=("ready",),
        source_name="GitHub Merge",
    ))
    stages.append(_merge_stage(mission_id, sources["github_merge"]))
    stages.append(_linked_or_capability_stage(
        "deployment_approval",
        "Deployment approval",
        mission_id,
        sources["deployment"],
        linked_keys=("approval_id", "approval"),
        ready_statuses=("configured",),
        source_name="Cloud Run Deployment",
    ))
    stages.append(_deployment_stage(mission_id, sources["deployment"]))
    stages.append(_verification_stage(mission_id, sources["verification"], sources["deployment"]))
    stages.append(_completion_stage(mission_id, stages))
    return stages


def _founder_request_stage(
    mission_id: str | None,
    active: dict[str, Any],
    same_active: bool,
) -> dict[str, Any]:
    if same_active and active.get("founder_request"):
        return _stage(
            "founder_request",
            "Founder request",
            "verified",
            {
                "mission_id": mission_id,
                "founder_request": active.get("founder_request"),
            },
            "Execution Mission",
            "high",
            "The active mission preserves the founder request under the same mission identity.",
        )
    return _stage("founder_request", "Founder request", "unknown", None, "Execution Mission", "low", "No founder request is linked to the inspected mission.")


def _mission_creation_stage(
    mission_id: str | None,
    active: dict[str, Any],
    same_active: bool,
) -> dict[str, Any]:
    if same_active:
        return _stage("mission_creation", "Mission creation", "verified", {"mission_id": mission_id, "created_at": active.get("created_at")}, "Execution Mission", "high", "An active mission record exists with the inspected mission identity.")
    return _stage("mission_creation", "Mission creation", "unknown", None, "Execution Mission", "low", "No mission record with the inspected identity was found.")


def _linked_or_capability_stage(
    stage_id: str,
    stage_name: str,
    mission_id: str | None,
    source: dict[str, Any],
    *,
    linked_keys: tuple[str, ...],
    ready_statuses: tuple[str, ...],
    source_name: str,
) -> dict[str, Any]:
    if _same_mission(source, mission_id) and any(source.get(key) for key in linked_keys):
        evidence = {key: source.get(key) for key in ("mission_id", *linked_keys) if source.get(key)}
        return _stage(stage_id, stage_name, "verified", evidence, source_name, "high", f"Mission-specific {stage_name.lower()} evidence is linked to the inspected mission.")
    status = str(source.get("status") or "unknown")
    if status in ready_statuses or status.endswith("-ready"):
        return _stage(stage_id, stage_name, "ready", {"capability_status": status}, source_name, "medium", f"The capability exists, but no mission-specific {stage_name.lower()} evidence was found.")
    if status in {"unavailable", "blocked"} or "awaiting" in status:
        return _stage(stage_id, stage_name, "blocked", {"capability_status": status}, source_name, "high", f"The capability reports a blocker and no mission-specific completion evidence exists.")
    return _stage(stage_id, stage_name, "unknown", {"capability_status": status}, source_name, "low", f"No mission-specific {stage_name.lower()} evidence was found.")


def _engineering_stage(mission_id: str | None, source: dict[str, Any]) -> dict[str, Any]:
    run = source.get("run") if isinstance(source.get("run"), dict) else source
    if _same_mission(run, mission_id) and (run.get("run_id") or str(run.get("status")) in {"in-progress", "completed"}):
        return _stage("engineering_execution", "Engineering execution", "verified", {"mission_id": mission_id, "run_id": run.get("run_id"), "status": run.get("status")}, "Engineering Manager", "high", "A mission-specific engineering run is present.")
    if _same_mission(run, mission_id) and run.get("breakdown_id"):
        return _stage("engineering_execution", "Engineering execution", "ready", _pick(run, "mission_id", "breakdown_id", "status"), "Engineering Manager", "high", "A mission-specific engineering handoff is prepared, but engineering execution has not started.")
    status = str(source.get("status") or "unknown")
    if status == "engineering-manager-ready":
        return _stage("engineering_execution", "Engineering execution", "manual", {"capability_status": status, "mode": source.get("mode")}, "Engineering Manager", "high", "Engineering planning exists, but no mission-specific execution run is linked; handoff to execution remains manual.")
    return _stage("engineering_execution", "Engineering execution", "unknown", {"capability_status": status}, "Engineering Manager", "low", "No engineering execution evidence is available.")


def _code_change_stage(mission_id: str | None, source: dict[str, Any]) -> dict[str, Any]:
    if _same_mission(source, mission_id) and (source.get("commit_sha") or source.get("files_changed") or source.get("writes_performed")):
        return _stage("code_changes", "Code changes", "verified", _pick(source, "mission_id", "execution_id", "branch_name", "commit_sha", "files_changed"), "GitHub Execution", "high", "GitHub write evidence is linked to the inspected mission.")
    status = str(source.get("status") or "unknown")
    if "awaiting" in status:
        return _stage("code_changes", "Code changes", "blocked", {"capability_status": status}, "GitHub Execution", "high", "GitHub execution is blocked by configuration and no mission-specific write evidence exists.")
    if status.endswith("-ready") or status == "ready":
        return _stage("code_changes", "Code changes", "ready", {"capability_status": status}, "GitHub Execution", "medium", "GitHub execution exists, but no mission-specific branch or commit linkage was found.")
    return _stage("code_changes", "Code changes", "unknown", {"capability_status": status}, "GitHub Execution", "low", "No mission-specific code-change evidence was found.")


def _pr_stage(mission_id: str | None, source: dict[str, Any]) -> dict[str, Any]:
    if source.get("mission_resolution_status") == "ambiguous":
        return _stage("pull_request", "Pull request", "unknown", _pick(source, "pr_number", "mission_resolution_status", "mission_resolution_evidence"), "PR Lifecycle", "high", "Conflicting pull-request evidence prevents a safe mission association.")
    if _same_mission(source, mission_id) and source.get("pr_number"):
        return _stage("pull_request", "Pull request", "verified", _pick(source, "mission_id", "pr_number", "pr_url", "head_branch"), "PR Lifecycle", "high", "A pull request is linked to the inspected mission.")
    status = str(source.get("status") or "unknown")
    if "awaiting" in status:
        return _stage("pull_request", "Pull request", "blocked", {"capability_status": status}, "PR Lifecycle", "high", "PR inspection is blocked and no mission-to-PR linkage exists.")
    if status == "ready" or status.endswith("-ready"):
        return _stage("pull_request", "Pull request", "ready", {"capability_status": status}, "PR Lifecycle", "medium", "PR capability exists, but no pull request is linked to the inspected mission.")
    return _stage("pull_request", "Pull request", "unknown", {"capability_status": status}, "PR Lifecycle", "low", "No mission-to-PR linkage was found.")


def _merge_stage(mission_id: str | None, source: dict[str, Any]) -> dict[str, Any]:
    if source.get("mission_resolution_status") == "ambiguous":
        return _stage("merge", "Merge", "unknown", _pick(source, "pr_number", "mission_resolution_status", "mission_resolution_evidence"), "GitHub Merge", "high", "Conflicting pull-request evidence prevents a safe mission association for this merge.")
    if _same_mission(source, mission_id) and source.get("merged") is True:
        return _stage("merge", "Merge", "verified", _pick(source, "mission_id", "pr_number", "merge_commit_sha", "pr_url"), "GitHub Merge", "high", "The mission-linked pull request is recorded as merged.")
    status = str(source.get("status") or "unknown")
    if "awaiting" in status:
        return _stage("merge", "Merge", "blocked", {"capability_status": status}, "GitHub Merge", "high", "Merge inspection is blocked and no mission-specific merge evidence exists.")
    if status == "ready":
        return _stage("merge", "Merge", "ready", {"capability_status": status}, "GitHub Merge", "medium", "Merge capability exists, but no mission-specific merge evidence was found.")
    return _stage("merge", "Merge", "unknown", {"capability_status": status}, "GitHub Merge", "low", "No mission-specific merge evidence was found.")


def _deployment_stage(mission_id: str | None, source: dict[str, Any]) -> dict[str, Any]:
    if _same_mission(source, mission_id) and (source.get("revision_name") or source.get("deployment_performed")):
        return _stage("production_deployment", "Production deployment", "verified", _pick(source, "mission_id", "revision_name", "service_url", "source_ref"), "Cloud Run Deployment", "high", "A Cloud Run revision is linked to the inspected mission.")
    status = str(source.get("status") or "unknown")
    if status == "configured":
        return _stage("production_deployment", "Production deployment", "ready", {"capability_status": status, "service_name": source.get("service_name")}, "Cloud Run Deployment", "medium", "Deployment capability is configured, but no mission-specific revision linkage was found.")
    return _stage("production_deployment", "Production deployment", "unknown", {"capability_status": status}, "Cloud Run Deployment", "low", "No mission-specific production deployment evidence was found.")


def _verification_stage(
    mission_id: str | None,
    source: dict[str, Any],
    deployment: dict[str, Any],
) -> dict[str, Any]:
    same_revision = bool(
        source.get("revision_name")
        and source.get("revision_name") == deployment.get("revision_name")
    )
    if (_same_mission(source, mission_id) or same_revision) and source.get("overall_result") == "pass":
        return _stage("verification", "Verification", "verified", _pick(source, "mission_id", "revision_name", "overall_result", "service_url"), "Production Verification", "high", "Passing verification is linked to the mission or its deployed revision.")
    status = str(source.get("status") or "unknown")
    if status == "ready":
        return _stage("verification", "Verification", "ready", {"capability_status": status, "service_url": source.get("service_url")}, "Production Verification", "medium", "Verification capability exists, but no result is linked to the mission or deployment revision.")
    return _stage("verification", "Verification", "unknown", {"capability_status": status}, "Production Verification", "low", "No mission-specific verification result was found.")


def _completion_stage(mission_id: str | None, prior: list[dict[str, Any]]) -> dict[str, Any]:
    verification = next(item for item in prior if item["stage_id"] == "verification")
    required = [item for item in prior if item["stage_id"] not in {"executive_recommendation", "merge_approval", "deployment_approval"}]
    if verification["status"] == "verified" and all(item["status"] == "verified" for item in required):
        return _stage("mission_completion", "Mission completion", "verified", {"mission_id": mission_id}, "Journey Inspector", "high", "All required mission stages and production verification are linked and verified.")
    if any(item["status"] == "blocked" for item in prior):
        return _stage("mission_completion", "Mission completion", "blocked", None, "Journey Inspector", "high", "At least one prerequisite stage is blocked.")
    return _stage("mission_completion", "Mission completion", "unknown", None, "Journey Inspector", "low", "Mission completion cannot be verified from the available linked evidence.")


def _build_transitions(
    mission_id: str | None,
    stages: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    resolution: dict[str, Any],
) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    for left, right in zip(stages, stages[1:]):
        if resolution["status"] != "resolved":
            transitions.append({
                "from_stage": left["stage_name"],
                "to_stage": right["stage_name"],
                "status": "unknown",
                "evidence": {
                    "mission_resolution": resolution["status"],
                    "source": "Journey Inspector mission resolution",
                },
                "evidence_source": "Journey Inspector mission resolution",
                "explanation": "Mission context is unavailable, so this transition cannot be inspected.",
            })
            continue
        status = _transition_status(left, right)
        evidence = _transition_evidence(mission_id, left, right, sources)
        if evidence.get("linked"):
            status = "verified"
        explanation = _transition_explanation(left, right, status, evidence)
        transitions.append({
            "from_stage": left["stage_name"],
            "to_stage": right["stage_name"],
            "status": status,
            "evidence": evidence or None,
            "evidence_source": evidence.get("source") if evidence else f"{left['evidence_source']} / {right['evidence_source']}",
            "explanation": explanation,
        })
    return transitions


def _transition_status(left: dict[str, Any], right: dict[str, Any]) -> str:
    if "blocked" in {left["status"], right["status"]}:
        return "blocked"
    if "manual" in {left["status"], right["status"]}:
        return "manual"
    return "unknown"


def _transition_evidence(
    mission_id: str | None,
    left: dict[str, Any],
    right: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not mission_id:
        return {}
    left_mission = _evidence_mission_id(left.get("evidence"))
    right_mission = _evidence_mission_id(right.get("evidence"))
    linked = bool(
        left["status"] == "verified"
        and right["status"] == "verified"
        and left_mission == mission_id
        and right_mission == mission_id
    )
    if left["stage_id"] == "merge" and right["stage_id"] == "deployment_approval":
        linked = linked and bool(sources["deployment"].get("pr_number") == sources["github_merge"].get("pr_number"))
    if left["stage_id"] == "production_deployment" and right["stage_id"] == "verification":
        deployment_revision = sources["deployment"].get("revision_name")
        linked = linked and bool(deployment_revision and deployment_revision == sources["verification"].get("revision_name"))
    return {"linked": linked, "mission_id": mission_id, "source": "Journey Inspector identity linkage"}


def _transition_explanation(
    left: dict[str, Any],
    right: dict[str, Any],
    status: str,
    evidence: dict[str, Any],
) -> str:
    if status == "verified":
        return f"The same mission identity links {left['stage_name']} to {right['stage_name']}."
    if status == "blocked":
        return f"The transition is blocked because {left['stage_name']} or {right['stage_name']} reports a blocker."
    if status == "manual":
        return f"The transition requires a manual handoff; no verified mission-specific linkage connects {left['stage_name']} to {right['stage_name']}."
    return f"No mission-specific linkage verifies the transition from {left['stage_name']} to {right['stage_name']}."


def _stage(
    stage_id: str,
    stage_name: str,
    status: str,
    evidence: Any,
    source: str,
    confidence: str,
    explanation: str,
) -> dict[str, Any]:
    assert status in STAGE_STATUSES
    return {
        "stage_id": stage_id,
        "stage_name": stage_name,
        "status": status,
        "evidence": evidence,
        "evidence_source": source,
        "evidence_scope": (
            "mission_specific"
            if status == "verified"
            else ("capability_only" if evidence is not None else "missing")
        ),
        "confidence": confidence,
        "explanation": explanation,
    }


def _same_mission(source: dict[str, Any], mission_id: str | None) -> bool:
    return bool(mission_id and str(source.get("mission_id") or "") == mission_id)


def _evidence_mission_id(evidence: Any) -> str | None:
    if isinstance(evidence, dict):
        value = str(evidence.get("mission_id") or "").strip()
        return value or None
    return None


def _pick(source: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: source.get(key) for key in keys if source.get(key) is not None}


def _journey_health(
    stages: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
) -> str:
    if all(item["status"] == "verified" for item in stages + transitions):
        return "complete"
    if any(item["status"] == "blocked" for item in stages + transitions):
        return "blocked"
    if any(item["status"] == "manual" for item in stages + transitions):
        return "manual-intervention-required"
    if any(item["status"] == "verified" for item in stages):
        return "partial"
    return "unknown"


def _reuse_recommendations(sources: dict[str, dict[str, Any]]) -> list[str]:
    labels = {
        "board_room": "Board Room recommendation",
        "founder_approval": "Founder Approval",
        "planning": "Planning",
        "engineering_manager": "Engineering Manager",
        "github_execution": "GitHub Execution",
        "github_pr": "PR Lifecycle",
        "github_merge": "Founder-approved Merge",
        "deployment": "Cloud Run Deployment",
        "verification": "Production Verification",
    }
    recommendations = []
    for key, label in labels.items():
        status = str(sources.get(key, {}).get("status") or "unknown")
        if status not in {"unknown", "unavailable"}:
            recommendations.append(f"Reuse {label}; capability status is {status}.")
    return recommendations


def _missing_linkages(
    mission_id: str | None,
    stages: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
) -> list[str]:
    missing = [
        f"{item['from_stage']} → {item['to_stage']}"
        for item in transitions
        if item["status"] != "verified"
    ]
    by_id = {item["stage_id"]: item for item in stages}
    if by_id["mission_creation"]["status"] == "verified" and by_id["engineering_execution"]["status"] != "verified":
        missing.append("Mission creation → Engineering execution")
    if by_id["mission_creation"]["status"] == "verified" and not _same_mission(sources["github_pr"], mission_id):
        missing.append("Mission creation → Pull request")
    pr_number = sources["github_pr"].get("pr_number")
    deployment_pr = sources["deployment"].get("pr_number")
    if pr_number and pr_number != deployment_pr:
        missing.append("Pull request → Production deployment")
    revision = sources["deployment"].get("revision_name")
    verified_revision = sources["verification"].get("revision_name")
    if revision and revision != verified_revision:
        missing.append("Production deployment → Verification")
    return list(dict.fromkeys(missing))


def _smallest_improvement(
    transition: dict[str, Any] | None,
    resolution: dict[str, Any],
) -> str:
    if resolution["status"] != "resolved":
        return "Resolve or preserve one canonical mission identity across the journey before diagnosing stage transitions."
    if not transition:
        return "No broken, manual, or unknown transition was identified."
    return (
        f"Connect existing {transition['from_stage']} evidence to {transition['to_stage']} "
        "using the same mission identity and record the handoff result."
    )


def mission_id_from_text(text: str) -> str | None:
    match = re.search(r"\b(?:EXEC|MISSION)-[A-Z0-9-]+\b", text.upper())
    return match.group(0) if match else None
