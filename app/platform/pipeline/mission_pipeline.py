from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.platform.executive_intelligence.board_room_integration import inspect_board_room_integration
from app.platform.deployment.approved_cloud_run import build_cloud_run_deployment_summary
from app.platform.deployment.approved_rollback import build_cloud_run_rollback_summary
from app.platform.deployment.production_verification import build_production_verification_summary
from app.platform.engineering_manager.service import build_engineering_manager_summary
from app.platform.execution.service import build_execution_summary
from app.platform.github_execution.approved_executor import build_approved_github_execution_summary
from app.platform.github_execution.approved_merge import build_github_merge_summary
from app.platform.github_execution.pr_lifecycle import build_github_pr_summary
from app.platform.planning.service import build_planning_summary
from app.platform.company_graph.service import build_company_graph
from app.platform.repository_intelligence.service import build_repository_intelligence_summary
from app.platform.operating_console.mission_run_service import find_latest_mission_run


PIPELINE_STAGES = ["planning", "engineering", "pr", "deploy", "verify", "complete"]
AUTO_STAGES = [
    "intent_received",
    "requirements_clarified",
    "scope_of_work",
    "architecture_review",
    "implementation_plan",
    "validation_plan",
    "founder_approval_required",
    "ready_for_execution",
]


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
        "active_missions": [mission for mission in missions if not mission.get("synthetic") and mission["status"] != "Complete"],
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
            if mission["mission_id"] == mission_id and not mission.get("synthetic"):
                return mission
        return None


def _source_systems() -> dict[str, dict[str, Any]]:
    return {
        "mission_runtime": _safe_call(find_latest_mission_run),
        "board_room": _safe_call(inspect_board_room_integration),
        "execution": _safe_call(build_execution_summary),
        "planning": _safe_call(build_planning_summary),
        "engineering_manager": _safe_call(build_engineering_manager_summary),
        "github_executor": _safe_call(build_approved_github_execution_summary),
        "github_pr": _safe_call(build_github_pr_summary),
        "github_merge": _safe_call(build_github_merge_summary),
        "deployment_manager": _safe_call(build_cloud_run_deployment_summary),
        "verification_service": _safe_call(build_production_verification_summary),
        "rollback_manager": _safe_call(build_cloud_run_rollback_summary),
        "repository_intelligence": _safe_call(build_repository_intelligence_summary),
        "company_graph": _safe_call(build_company_graph),
    }


def _derive_primary_mission(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    runtime = sources.get("mission_runtime") or {}
    execution_mission = sources.get("execution", {}).get("active_mission") or {}
    if runtime.get("found"):
        runtime_context = runtime.get("context") or {}
        matching_execution = execution_mission if execution_mission.get("mission_id") == runtime.get("mission_id") else {}
        execution_mission = {**matching_execution, **runtime_context, "mission_id": runtime.get("mission_id"), "workflow_run_id": runtime.get("workflow_run_id"), "runtime_state": runtime}
    synthetic = not bool(execution_mission.get("mission_id"))
    mission_id = str(execution_mission.get("mission_id") or "MISSION-CONTROL-001")
    founder_request = str(execution_mission.get("founder_request") or "Unify Mission Control into a founder-facing Mission Operating System.")
    title = _intelligent_title(founder_request, str(execution_mission.get("title") or ""))
    suggested_files = _suggest_files(founder_request, sources)
    complexity = _complexity(suggested_files, founder_request)
    risk = _risk(suggested_files, complexity, founder_request)
    validation_plan = _validation_plan(suggested_files)
    branch_name = _branch_name(title)
    scope = _scope(founder_request, suggested_files, complexity, risk)
    auto_progress = _durable_auto_progress(runtime) if runtime.get("found") else _unlinked_progress() if synthetic else _auto_progress(founder_request, suggested_files, sources, validation_plan)
    status = _derive_status(sources, execution_mission, runtime)
    recommendation = _recommendation(status, sources, runtime)
    health = _mission_health(status, recommendation, sources)
    progress = _mission_progress(status, sources, execution_mission, runtime)
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
        "workflow_run_id": execution_mission.get("workflow_run_id"),
        "synthetic": synthetic,
        "mission_label": f"Mission {mission_id}: {title}",
        "title": title,
        "branch_name": branch_name,
        "suggested_files": suggested_files,
        "complexity": complexity,
        "risk": risk,
        "validation_plan": validation_plan,
        "auto_generated_scope": scope,
        "auto_progress": auto_progress,
        "current_autonomous_stage": auto_progress["current_stage"],
        "auto_progress_next": auto_progress["next"],
        "approval_gate": auto_progress["approval_gate"],
        "what": founder_request,
        "founder_request": founder_request,
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
            "mission_runtime": _compact(sources["mission_runtime"]),
            "board_room": _compact(sources["board_room"]),
            "planning": _compact(sources["planning"]),
            "engineering_manager": _compact(sources["engineering_manager"]),
            "github_executor": _compact(sources["github_executor"]),
            "github_pr": _compact(sources["github_pr"]),
            "github_merge": _compact(sources["github_merge"]),
            "deployment_manager": _compact(sources["deployment_manager"]),
            "verification_service": _compact(sources["verification_service"]),
            "rollback_manager": _compact(sources["rollback_manager"]),
            "repository_intelligence": _compact(sources["repository_intelligence"]),
            "company_graph": _compact(sources["company_graph"]),
        },
        "governance": _governance(),
    }


def _intelligent_title(request: str, existing_title: str) -> str:
    text = request.lower()
    generic = {"", "execution mission", "implementation-request", "implementation request"}
    if existing_title.strip().lower() not in generic and "implementation-request" not in existing_title.lower():
        return existing_title.strip()
    if "ui" in text and any(word in text for word in ["polish", "dashboard", "founder"]):
        return "Improve Founder Dashboard UI Polish"
    if "board room" in text and any(word in text for word in ["improve", "intelligence", "adaptive"]):
        return "Enhance Board Room Intelligence"
    if "deployment" in text and any(word in text for word in ["fix", "verify", "verification"]):
        return "Fix Deployment Verification Flow"
    if "pipeline" in text or "mission operating system" in text:
        return "Advance Mission Operating System"
    return _title(request)


def _branch_name(title: str) -> str:
    skip = {"improve", "enhance", "fix", "add", "create", "build", "the", "a", "an"}
    words = ["".join(ch for ch in word.lower() if ch.isalnum()) for word in title.split()]
    parts = [word for word in words if word and word not in skip]
    return "mc-" + "-".join(parts[:6] or ["mission"])


def _suggest_files(request: str, sources: dict[str, dict[str, Any]]) -> list[str]:
    text = request.lower()
    files: list[str] = []
    if any(word in text for word in ["ui", "dashboard", "founder", "polish", "settings"]):
        files.extend([
            "app/platform/ui/founder_dashboard_stable.py",
            "app/platform/ui/dashboard_browser_script.py",
            "app/platform/ui/mission_pipeline_ui.py",
        ])
    if "board room" in text or "conversation" in text:
        files.extend([
            "app/platform/operating_console/service.py",
            "app/platform/ui/founder_dashboard_board_chat.py",
        ])
    if "pipeline" in text or "mission operating system" in text:
        files.extend([
            "app/platform/pipeline/mission_pipeline.py",
            "app/platform/ui/mission_pipeline_ui.py",
            "app/platform/server.py",
        ])
    if "deploy" in text or "deployment" in text:
        files.extend([
            "app/platform/deployment/approved_cloud_run.py",
            "app/platform/deployment/production_verification.py",
        ])
    if "github" in text or "pr" in text:
        files.extend([
            "app/platform/github_execution/approved_executor.py",
            "app/platform/github_execution/pr_lifecycle.py",
        ])
    return sorted(set(files or ["Determine exact files from Repository Intelligence before execution."]))[:6]


def _complexity(files: list[str], request: str) -> str:
    if len(files) <= 2 and not any(word in request.lower() for word in ["deploy", "rollback", "auth", "database"]):
        return "Low"
    if len(files) <= 5:
        return "Medium"
    return "High"


def _risk(files: list[str], complexity: str, request: str) -> str:
    text = request.lower()
    if any(word in text for word in ["auth", "secret", "deploy", "rollback", "traffic", "database"]):
        return "High" if complexity == "High" else "Medium"
    if any("deployment" in file or "github_execution" in file for file in files):
        return "Medium"
    return "Low"


def _validation_plan(files: list[str]) -> list[str]:
    checks = ["python3 -m compileall app/platform"]
    if any("/ui/" in file for file in files):
        checks.extend([
            "python3 -m app.platform.ui.login_module_boundary_check",
            "python3 -m app.platform.ui.ui_module_size_check",
            "Dashboard render check",
            "node --check generated dashboard JS",
        ])
    if any("/deployment/" in file for file in files):
        checks.append("Preview deployment only; no live deploy without founder approval")
    if any("/github_execution/" in file for file in files):
        checks.append("Preview GitHub execution only; no live GitHub write without founder approval")
    return list(dict.fromkeys(checks))


def _scope(request: str, files: list[str], complexity: str, risk: str) -> dict[str, Any]:
    return {
        "summary": f"Implement the mission intent: {request}",
        "estimated_files": len(files),
        "estimated_tasks": max(3, min(len(files) + 2, 8)),
        "complexity": complexity,
        "risk": risk,
        "out_of_scope": ["Direct merge", "Live deployment", "Rollback execution", "Traffic shift without founder approval"],
    }


def _auto_progress(request: str, files: list[str], sources: dict[str, dict[str, Any]], validation_plan: list[str]) -> dict[str, Any]:
    stages = [
        _auto_stage("intent_received", "Intent Received", "auto-completed", "Founder request captured from existing mission/request context."),
        _auto_stage("requirements_clarified", "Requirements Clarified", "auto-completed", "Founder request analyzed and converted into mission intent."),
        _auto_stage("scope_of_work", "Scope Of Work", "auto-completed", f"Scope generated for {len(files)} likely file(s)."),
        _auto_stage("architecture_review", "Architecture Review", "auto-completed", f"Company graph observed: {sources['company_graph'].get('status', 'available')}."),
        _auto_stage("implementation_plan", "Implementation Plan", "auto-completed", f"Engineering Manager observed: {sources['engineering_manager'].get('status', 'available')}."),
        _auto_stage("validation_plan", "Validation Plan", "auto-completed", f"{len(validation_plan)} validation step(s) generated."),
        _auto_stage("founder_approval_required", "Founder Approval Required", "waiting-for-founder", "Autonomous planning pauses here for founder governance approval."),
        _auto_stage("ready_for_execution", "Ready For Execution", "queued", "Delegates to existing GitHub Execution after approval."),
    ]
    return {
        "mode": "computed-state-machine",
        "stores_state": False,
        "auto_advancing": False,
        "current_stage": "founder_approval_required",
        "next": "Founder approval required before any GitHub write, merge, deploy, or rollback.",
        "approval_gate": "Founder approval required",
        "stages": stages,
    }


def _auto_stage(key: str, label: str, state: str, detail: str) -> dict[str, str]:
    return {"key": key, "label": label, "state": state, "detail": detail}


def _derive_status(sources: dict[str, dict[str, Any]], execution_mission: dict[str, Any], runtime: dict[str, Any]) -> str:
    if runtime.get("found"):
        stage = str(runtime.get("current_stage") or "unknown")
        if stage == "change_set_ready":
            return "Change Set Ready"
        if stage == "blocked":
            return "Blocked"
        if stage == "failed":
            return "Failed"
        return "Preparation In Progress"
    if not execution_mission:
        return "Not Linked"
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


def _recommendation(status: str, sources: dict[str, dict[str, Any]], runtime: dict[str, Any]) -> dict[str, str]:
    if runtime.get("found"):
        error = runtime.get("error") if isinstance(runtime.get("error"), dict) else {}
        if error.get("classification") == "authorization_resume_required":
            return {"action": "Resume the authenticated founder session", "blocker": "Founder session restoration required", "confidence": "High", "actor": "Founder"}
        if status == "Change Set Ready":
            return {"action": "Review the prepared change set", "blocker": "Waiting for engineering execution approval", "confidence": "High", "actor": "Founder"}
        if status in {"Blocked", "Failed"}:
            return {"action": "Review the preserved runtime failure", "blocker": str(error.get("classification") or "Mission preparation blocked"), "confidence": "High", "actor": "Founder"}
        return {"action": "Monitor durable mission preparation", "blocker": "None", "confidence": "High", "actor": "Mission Runtime"}
    if status == "Not Linked":
        return {"action": "Open or create a canonical mission", "blocker": "No durable mission run is linked", "confidence": "High", "actor": "Founder"}
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


def _mission_progress(status: str, sources: dict[str, dict[str, Any]], execution_mission: dict[str, Any], runtime: dict[str, Any]) -> int | None:
    if runtime.get("found"):
        stages = {str(item.get("specialist_stage")) for item in runtime.get("steps") or [] if item.get("status") == "completed"}
        expected = {"accepted", "planning", "capability_intelligence", "repository_intelligence", "architecture_agent", "architecture_validation", "engineering_manager", "change_set_generation", "change_set_validation", "change_set_ready"}
        return min(100, round(100 * len(stages & expected) / len(expected)))
    if not execution_mission:
        return None
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


def _durable_auto_progress(runtime: dict[str, Any]) -> dict[str, Any]:
    steps = runtime.get("steps") or []
    current = str(runtime.get("current_stage") or "unknown")
    return {
        "mode": "durable-runtime-projection",
        "stores_state": False,
        "auto_advancing": False,
        "current_stage": current,
        "next": "Review prepared changes" if current == "change_set_ready" else "Restore founder session" if (runtime.get("error") or {}).get("classification") == "authorization_resume_required" else "Monitor mission preparation",
        "approval_gate": "engineering_execution" if current == "change_set_ready" else "none",
        "stages": [{"name": item.get("specialist_stage"), "label": str(item.get("specialist_stage") or "Unknown").replace("_", " ").title(), "state": item.get("status"), "detail": item.get("result_summary")} for item in steps],
    }


def _unlinked_progress() -> dict[str, Any]:
    return {"mode": "unlinked", "stores_state": False, "auto_advancing": False, "current_stage": "unknown", "next": "Resolve a canonical durable mission link", "approval_gate": "unknown", "stages": []}


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


def _executive_summary(mission_id: str, title: str, status: str, recommendation: dict[str, str], health: dict[str, str], progress: int | None) -> str:
    progress_label = f"{progress}%" if progress is not None else "unknown because no durable run is linked"
    return (
        f"Mission {mission_id}: {title}. "
        f"Status: {status}. Health: {health['label']}. Progress: {progress_label}. "
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
        "synthetic": bool(mission.get("synthetic")),
        "mission_label": mission["mission_label"],
        "title": mission["title"],
        "branch_name": mission["branch_name"],
        "suggested_files": mission["suggested_files"],
        "complexity": mission["complexity"],
        "risk": mission["risk"],
        "validation_plan": mission["validation_plan"],
        "auto_progress": mission["auto_progress"],
        "current_autonomous_stage": mission["current_autonomous_stage"],
        "auto_progress_next": mission["auto_progress_next"],
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
    canonical = [mission for mission in missions if not mission.get("synthetic")]
    blocked = sum(1 for mission in canonical if mission["blocking_reason"] not in {"None", "No rollback needed yet"})
    complete = sum(1 for mission in canonical if mission["status"] == "Complete")
    return {"total": len(canonical), "active": len(canonical) - complete, "blocked": blocked, "complete": complete}


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
