from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.platform.board_room.service import build_board_room_summary
from app.platform.deployment.approved_cloud_run import build_cloud_run_deployment_summary
from app.platform.deployment.approved_rollback import build_cloud_run_rollback_summary
from app.platform.deployment.production_verification import build_production_verification_summary
from app.platform.engineering_manager.service import build_engineering_manager_summary
from app.platform.execution.service import build_execution_summary
from app.platform.github_execution.approved_executor import build_approved_github_execution_summary
from app.platform.github_execution.approved_merge import build_github_merge_summary
from app.platform.github_execution.pr_lifecycle import build_github_pr_summary
from app.platform.planning.service import build_planning_summary


PIPELINE_STAGES = ["planning", "engineering", "pr", "deploy", "verify", "complete"]


def build_mission_pipeline_summary() -> dict[str, Any]:
    snapshot = MissionAggregator().snapshot()
    missions = [_mission_card(mission) for mission in snapshot["missions"]]
    return {
        "company": "AI Software Factory",
        "product": "Mission Operating System",
        "milestone": "MC-PIPELINE-01",
        "status": "mission-pipeline-observer-ready",
        "mode": "read-only-aggregator",
        "purpose": "Observe existing Mission Control systems and present a founder-first mission view with recommendations and blockers.",
        "missions": missions,
        "active_missions": [mission for mission in missions if mission["status"] != "Complete"],
        "summary": _summary(missions),
        "governance": _governance(),
        "endpoints": {
            "summary": "GET /mission-control/pipeline",
            "detail": "GET /mission-control/pipeline/{mission_id}",
            "timeline": "GET /mission-control/pipeline/{mission_id}/timeline",
            "recommendation": "GET /mission-control/pipeline/{mission_id}/recommendation",
        },
        "source_systems": snapshot["source_systems"],
    }


def get_pipeline_mission(mission_id: str) -> dict[str, Any]:
    mission = MissionAggregator().mission(mission_id)
    if not mission:
        return {"status": "mission-not-found", "mission_id": mission_id}
    return {"status": "pipeline-mission-observed", "mission": mission}


def get_pipeline_mission_timeline(mission_id: str) -> dict[str, Any]:
    mission = MissionAggregator().mission(mission_id)
    if not mission:
        return {"status": "mission-not-found", "mission_id": mission_id, "timeline": []}
    return {"status": "pipeline-timeline-observed", "mission_id": mission_id, "timeline": mission["timeline"]}


def get_pipeline_mission_recommendation(mission_id: str) -> dict[str, Any]:
    mission = MissionAggregator().mission(mission_id)
    if not mission:
        return {"status": "mission-not-found", "mission_id": mission_id}
    return {"status": "pipeline-recommendation-ready", "mission_id": mission_id, "recommendation": mission["recommendation"]}


class MissionAggregator:
    """Aggregates mission state from existing systems without owning or storing it."""

    def snapshot(self) -> dict[str, Any]:
        source_systems = _source_systems()
        mission = _derive_primary_mission(source_systems)
        return {"missions": [mission], "source_systems": _source_system_status(source_systems)}

    def mission(self, mission_id: str) -> dict[str, Any] | None:
        missions = self.snapshot()["missions"]
        for mission in missions:
            if mission["mission_id"] == mission_id:
                return mission
        return None


def _source_systems() -> dict[str, dict[str, Any]]:
    return {
        "board_room": _safe_call(build_board_room_summary),
        "execution": _safe_call(build_execution_summary),
        "planning": _safe_call(build_planning_summary),
        "engineering_manager": _safe_call(build_engineering_manager_summary),
        "github_executor": _safe_call(build_approved_github_execution_summary),
        "github_pr": _safe_call(build_github_pr_summary),
        "github_merge": _safe_call(build_github_merge_summary),
        "deployment_manager": _safe_call(build_cloud_run_deployment_summary),
        "verification_service": _safe_call(build_production_verification_summary),
        "rollback_manager": _safe_call(build_cloud_run_rollback_summary),
    }


def _derive_primary_mission(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    execution_mission = sources.get("execution", {}).get("active_mission") or {}
    mission_id = str(execution_mission.get("mission_id") or "MISSION-CONTROL-001")
    founder_request = str(execution_mission.get("founder_request") or "Unify Mission Control into a founder-facing Mission Operating System.")
    title = str(execution_mission.get("title") or _title(founder_request))
    status = _derive_status(sources, execution_mission)
    recommendation = _recommendation(status, sources)
    health = _mission_health(status, recommendation, sources)
    progress = _mission_progress(status, sources, execution_mission)
    business_value = _business_value(founder_request, sources)
    owner = _current_owner(status, recommendation)
    eta = _mission_eta(status, sources)
    confidence = _mission_confidence(status, health, recommendation, sources)
    objective = _mission_objective(founder_request)
    success_criteria = _success_criteria(founder_request)
    executive_summary = _executive_summary(mission_id, title, status, recommendation, health, progress)
    timeline = _timeline(mission_id, founder_request, sources, execution_mission, recommendation)
    return {
        "mission_id": mission_id,
        "mission_label": f"Mission {mission_id}: {title}",
        "title": title,
        "what": founder_request,
        "objective": objective,
        "success_criteria": success_criteria,
        "why": "Give the founder one operating view from planning through engineering, PR, deployment, verification, and rollback.",
        "who": "Founder, Board Room, Engineering Manager, GitHub Executor, Deployment Manager, Verification Service, Rollback Manager",
        "status": status,
        "health": health,
        "progress_percentage": progress,
        "business_value": business_value,
        "executive_summary": executive_summary,
        "current_owner": owner,
        "eta": eta,
        "mission_confidence": confidence,
        "next_action": recommendation["action"],
        "blocking_reason": recommendation["blocker"],
        "recommendation": recommendation,
        "timeline": timeline,
        "source_snapshot": {
            "board_room": _compact(sources["board_room"]),
            "planning": _compact(sources["planning"]),
            "engineering_manager": _compact(sources["engineering_manager"]),
            "github_executor": _compact(sources["github_executor"]),
            "github_pr": _compact(sources["github_pr"]),
            "github_merge": _compact(sources["github_merge"]),
            "deployment_manager": _compact(sources["deployment_manager"]),
            "verification_service": _compact(sources["verification_service"]),
            "rollback_manager": _compact(sources["rollback_manager"]),
        },
        "governance": _governance(),
    }


def _derive_status(sources: dict[str, dict[str, Any]], execution_mission: dict[str, Any]) -> str:
    verification_status = str(sources["verification_service"].get("status") or "")
    deployment_status = str(sources["deployment_manager"].get("status") or "")
    github_status = str(sources["github_executor"].get("status") or "")
    engineering_status = str(sources["engineering_manager"].get("status") or "")
    if verification_status in {"verification-complete", "ready"} and deployment_status == "ready":
        return "Verification Ready"
    if deployment_status == "ready":
        return "Deployment Ready"
    if github_status == "ready":
        return "PR Execution Ready"
    if engineering_status == "engineering-manager-ready":
        return "Engineering Ready"
    if execution_mission:
        return "Planning Active"
    return "Planning Ready"


def _recommendation(status: str, sources: dict[str, dict[str, Any]]) -> dict[str, str]:
    deployment_status = str(sources["deployment_manager"].get("status") or "")
    github_status = str(sources["github_executor"].get("status") or "")
    verification_status = str(sources["verification_service"].get("status") or "")
    rollback_status = str(sources["rollback_manager"].get("status") or "")
    if verification_status == "failed":
        return {"action": "Rollback recommended", "blocker": "Production unhealthy", "confidence": "High", "actor": "Founder"}
    if status == "Verification Ready":
        return {"action": "Run production verification", "blocker": "Waiting for verification result", "confidence": "High", "actor": "Founder"}
    if deployment_status == "ready":
        return {"action": "Preview deployment", "blocker": "Waiting for deploy approval", "confidence": "High", "actor": "Founder"}
    if github_status == "ready":
        return {"action": "Preview GitHub execution or review PR lifecycle", "blocker": "Waiting for approved PR workflow", "confidence": "Medium", "actor": "Founder"}
    if rollback_status == "ready":
        return {"action": "Keep rollback available if verification fails", "blocker": "No rollback needed yet", "confidence": "Medium", "actor": "Rollback Manager"}
    return {"action": "Create or approve the next mission artifact in existing Mission Control tools", "blocker": "Waiting for founder direction", "confidence": "Medium", "actor": "Founder"}


def _mission_health(status: str, recommendation: dict[str, str], sources: dict[str, dict[str, Any]]) -> dict[str, str]:
    verification_status = str(sources["verification_service"].get("status") or "")
    blocker = recommendation["blocker"]
    if verification_status == "failed" or "Rollback recommended" in recommendation["action"]:
        return {"label": "Failed", "icon": "X", "meaning": "Critical failure; rollback or intervention required."}
    if status == "Complete" or verification_status == "passed":
        return {"label": "Completed", "icon": "OK", "meaning": "Mission finished successfully."}
    if blocker and blocker not in {"None", "No rollback needed yet"} and "Waiting for founder" in blocker:
        return {"label": "Blocked", "icon": "BLOCKED", "meaning": "Cannot proceed until founder or operator intervention."}
    if blocker and blocker not in {"None", "No rollback needed yet"}:
        return {"label": "Warning", "icon": "WARN", "meaning": "Minor issue or pending step, not necessarily blocking."}
    return {"label": "Healthy", "icon": "OK", "meaning": "All observed systems normal."}


def _mission_progress(status: str, sources: dict[str, dict[str, Any]], execution_mission: dict[str, Any]) -> int:
    completed = 0
    if execution_mission or sources["board_room"].get("status"):
        completed += 1
    if sources["engineering_manager"].get("status") == "engineering-manager-ready":
        completed += 1
    if sources["github_executor"].get("status") == "ready":
        completed += 1
    if sources["deployment_manager"].get("status") == "ready":
        completed += 1
    if status in {"Verification Ready", "Complete"} or sources["verification_service"].get("status") in {"ready", "passed"}:
        completed += 1
    return min(100, int((completed / 5) * 100))


def _mission_objective(founder_request: str) -> str:
    request = founder_request.strip().rstrip(".")
    return request or "Unify Mission Control into an executive mission operating system"


def _success_criteria(founder_request: str) -> list[str]:
    return [
        "Founder can understand mission health, progress, owner, ETA, confidence, blocker, and next action at a glance.",
        "Mission details tell the full story from request to current recommendation.",
        "All executive fields are derived from existing systems without new state storage.",
    ]


def _business_value(founder_request: str, sources: dict[str, dict[str, Any]]) -> dict[str, str]:
    text = founder_request.lower()
    if any(word in text for word in ["pipeline", "mission", "operating system", "dashboard"]):
        return {"impact": "High", "risk": "Low", "description": "Reduces founder decision time by consolidating scattered execution signals into one mission view."}
    if any(word in text for word in ["deploy", "rollback", "production", "github", "pr"]):
        return {"impact": "High", "risk": "Medium", "description": "Improves governed delivery speed while preserving explicit approval gates."}
    return {"impact": "Medium", "risk": "Low", "description": "Improves Mission Control clarity and keeps founder attention on the next decision."}


def _current_owner(status: str, recommendation: dict[str, str]) -> str:
    if recommendation.get("actor"):
        return recommendation["actor"]
    if status == "Engineering Ready":
        return "Engineering Manager"
    if status == "PR Execution Ready":
        return "GitHub Executor"
    if status == "Deployment Ready":
        return "Deployment Manager"
    if status == "Verification Ready":
        return "Verification Service"
    return "Founder"


def _mission_eta(status: str, sources: dict[str, dict[str, Any]]) -> str:
    if status == "Verification Ready":
        return "Estimated: 2-3 minutes for production verification"
    if status == "Deployment Ready":
        return "Estimated: 3-5 minutes for deployment plus verification"
    if status == "PR Execution Ready":
        return "Estimated: 5-10 minutes after PR review and merge approval"
    if status == "Engineering Ready":
        return "Estimated: not computable until implementation package and PR exist"
    if status == "Complete":
        return "Complete"
    return "Not computable"


def _mission_confidence(status: str, health: dict[str, str], recommendation: dict[str, str], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if health["label"] == "Failed":
        return {"score": 0, "reason": "Verification or production health indicates failure. Rollback review required."}
    if health["label"] == "Completed":
        return {"score": 100, "reason": "Mission is complete."}
    if status == "Verification Ready":
        return {"score": 88, "reason": "Deployment and verification services are available; final production check remains."}
    if status == "Deployment Ready":
        return {"score": 82, "reason": "Deployment manager is ready; founder approval and verification remain."}
    if status == "PR Execution Ready":
        return {"score": 72, "reason": "GitHub execution is available; PR details and merge approval remain."}
    return {"score": 55, "reason": "Mission is observable, but more execution data is needed for higher confidence."}


def _executive_summary(mission_id: str, title: str, status: str, recommendation: dict[str, str], health: dict[str, str], progress: int) -> str:
    return (
        f"Mission {mission_id}: {title}. "
        f"Status: {status}. Health: {health['label']}. Progress: {progress}%. "
        f"Current blocker: {recommendation['blocker']}. "
        f"Recommendation: {recommendation['action']}."
    )


def _timeline(mission_id: str, founder_request: str, sources: dict[str, dict[str, Any]], execution_mission: dict[str, Any], recommendation: dict[str, str]) -> list[dict[str, Any]]:
    created = str(execution_mission.get("created_at") or _now())
    events = [
        _event(created, "Founder", f"Founder requested: {founder_request}", "founder_request"),
        _event(created, "Board Room", f"Board Room capability observed: {sources['board_room'].get('status', 'ready')}", "board_room"),
        _event(_now(), "Planning", f"Planning service observed: {sources['planning'].get('status', 'unknown')}", "planning"),
        _event(_now(), "Engineering Manager", f"Engineering Manager observed: {sources['engineering_manager'].get('status', 'unknown')}", "engineering"),
        _event(_now(), "GitHub Executor", f"GitHub execution observed: {sources['github_executor'].get('status', 'unknown')}", "github"),
        _event(_now(), "Deployment Manager", f"Deployment manager observed: {sources['deployment_manager'].get('status', 'unknown')}", "deployment"),
        _event(_now(), "Verification Service", f"Verification service observed: {sources['verification_service'].get('status', 'unknown')}", "verification"),
        _event(_now(), "Mission OS", f"Now: {recommendation['action']} ({recommendation['blocker']})", "recommendation"),
    ]
    return sorted(events, key=lambda event: event["timestamp"])


def _mission_card(mission: dict[str, Any]) -> dict[str, Any]:
    return {
        "mission_id": mission["mission_id"],
        "mission_label": mission["mission_label"],
        "title": mission["title"],
        "status": mission["status"],
        "health": mission["health"],
        "progress_percentage": mission["progress_percentage"],
        "current_owner": mission["current_owner"],
        "eta": mission["eta"],
        "business_value": mission["business_value"],
        "mission_confidence": mission["mission_confidence"],
        "next_action": mission["next_action"],
        "blocking_reason": mission["blocking_reason"],
        "confidence": mission["recommendation"]["confidence"],
    }


def _summary(missions: list[dict[str, Any]]) -> dict[str, int]:
    blocked = sum(1 for mission in missions if mission["blocking_reason"] not in {"None", "No rollback needed yet"})
    complete = sum(1 for mission in missions if mission["status"] == "Complete")
    return {"total": len(missions), "active": len(missions) - complete, "blocked": blocked, "complete": complete}


def _source_system_status(sources: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {name: str(data.get("status") or "unknown") for name, data in sources.items()}


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if key in {"status", "product", "milestone", "next_step", "repository", "service_name", "region"}}


def _event(timestamp: str, actor: str, detail: str, source: str) -> dict[str, str]:
    return {"timestamp": timestamp, "actor": actor, "detail": detail, "source": source}


def _safe_call(fn: Any) -> dict[str, Any]:
    try:
        result = fn()
        return result if isinstance(result, dict) else {"status": "unknown", "value": str(result)}
    except Exception as exc:  # pragma: no cover - defensive observer boundary
        return {"status": "unavailable", "error": str(exc)[:200]}


def _governance() -> dict[str, bool]:
    return {
        "observer_only": True,
        "stores_state": False,
        "database_tables_created": False,
        "uses_existing_components": True,
        "github_mutation": False,
        "branch_creation": False,
        "pr_creation": False,
        "merge": False,
        "deployment": False,
        "traffic_shift": False,
        "rollback_execution": False,
    }


def _title(request: str) -> str:
    return (" ".join(request.split())[:80].strip().rstrip(".")) or "Mission Operating System"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
