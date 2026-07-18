import json
import os
from typing import Any, Dict, List, Optional

import requests

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformWorkflowRun, PlatformWorkflowStepRun
from app.platform.persistence.operational_evidence import latest_operational_record, record_operational_evidence


GATE_NAMES = ("proposal", "mission", "planning", "architecture", "engineering", "validation", "pr", "merge", "deploy", "production_verified")


def sprint_authority() -> Dict[str, Any]:
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        run = db.query(PlatformWorkflowRun).filter(PlatformWorkflowRun.workflow_name == "Durable Board Room Mission Run").order_by(PlatformWorkflowRun.updated_at.desc()).first()
        if run is None:
            return {"status": "unknown", "unknown_reason": "No durable mission workflow exists from which to derive the current sprint."}
        state = _workflow_state(db, run.workflow_run_id)
        context = state.get("context") if isinstance(state.get("context"), dict) else {}
        gates = _runtime_gates(run.plan_status, run.status)
        completed = sum(1 for gate in gates if gate["status"] == "completed")
        return {
            "status": "active" if run.status not in {"completed", "failed", "blocked"} else run.status,
            "sprint_id": "SPRINT-%s" % run.workflow_run_id,
            "workflow_run_id": run.workflow_run_id,
            "mission_id": state.get("mission_id"),
            "goals": [str(context.get("founder_request") or context.get("title") or run.workflow_name)],
            "gates": gates,
            "progress": {"completed": completed, "total": len(gates), "percentage": round(100.0 * completed / len(gates), 1)},
            "completion": run.status == "completed",
            "updated_at": _iso(run.updated_at),
            "authority": "platform_workflow_runs",
        }
    finally:
        db.close()


def verification_authority() -> Dict[str, Any]:
    record = latest_operational_record("production_verification")
    current_revision = os.getenv("K_REVISION")
    recorded_revision = (record or {}).get("payload", {}).get("revision_name")
    if current_revision and recorded_revision != current_revision:
        from app.platform.deployment.production_verification import run_automatic_production_verification
        result = run_automatic_production_verification()
        return {"status": "verification-complete", **result, "authority": "production_verification_service"}
    if not record:
        return {"status": "unknown", "unknown_reason": "No durable production verification record exists."}
    return {"status": "verification-complete", **record["payload"], "verified_at": record["observed_at"], "authority": record["authority"]}


def release_authority() -> Dict[str, Any]:
    live = _cloud_run_release()
    if live.get("status") != "unknown":
        existing = latest_operational_record("release", str(live.get("service") or "production"))
        existing_revision = (existing or {}).get("payload", {}).get("active_revision")
        if existing_revision != live.get("active_revision"):
            record_operational_evidence("release", "cloud_run_admin_api", str(live.get("service") or "production"), "observed", live)
        return live
    record = latest_operational_record("release")
    if record:
        return {"status": "release-observed", **record["payload"], "recorded_at": record["observed_at"], "authority": record["authority"], "live_error": live.get("unknown_reason")}
    return live


def project_gates(mission: Dict[str, Any], github: Dict[str, Any], release: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
    active = mission.get("active_mission", {}).get("value") or {}
    stage = str(mission.get("mission_stage", {}).get("value") or "")
    has_mission = bool(active.get("mission_id"))
    open_prs = github.get("open_prs", {}).get("value") or []
    latest_merge = github.get("latest_merge", {}).get("value")
    deployed = release.get("status") != "unknown" and bool(release.get("active_revision") or release.get("revision"))
    verified = verification.get("status") == "verification-complete" and verification.get("overall_result") == "pass"
    engineering_ready = stage in {"change_set_ready", "Change Set Ready", "pr", "deploy", "verify", "complete"}
    gate_values = {
        "proposal": has_mission,
        "mission": has_mission,
        "planning": has_mission and stage not in {"", "accepted", "intent_received"},
        "architecture": engineering_ready,
        "engineering": engineering_ready,
        "validation": engineering_ready,
        "pr": bool(open_prs or latest_merge),
        "merge": bool(latest_merge),
        "deploy": deployed,
        "production_verified": verified,
    }
    gates = [{"name": name, "status": "completed" if gate_values[name] else "pending", "completed": gate_values[name]} for name in GATE_NAMES]
    completed = sum(1 for item in gates if item["completed"])
    return {"status": "observed", "gates": gates, "completed_gates": completed, "total_gates": len(gates), "percentage": round(100.0 * completed / len(gates), 1), "complete": completed == len(gates), "authority": "derived_from_canonical_operational_evidence"}


def _cloud_run_release() -> Dict[str, Any]:
    service = os.getenv("K_SERVICE")
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION", "asia-southeast1")
    if not service or not project:
        revision = os.getenv("K_REVISION")
        if revision:
            return {"status": "release-observed", "stage": "production", "service": service, "active_revision": revision, "deployment_history": [{"revision": revision, "observed_at": os.getenv("SOURCE_COMMIT_TIMESTAMP")}], "traffic": None, "authority": "cloud_run_runtime"}
        return {"status": "unknown", "unknown_reason": "Cloud Run service identity is unavailable outside the deployed runtime."}
    token = _metadata_token()
    if not token:
        return {"status": "unknown", "unknown_reason": "Cloud Run control-plane credentials are unavailable."}
    base = "https://run.googleapis.com/v2/projects/%s/locations/%s" % (project, region)
    headers = {"Authorization": "Bearer %s" % token}
    service_response = requests.get("%s/services/%s" % (base, service), headers=headers, timeout=8)
    service_resource = "projects/%s/locations/%s/services/%s" % (project, region, service)
    revisions_response = requests.get("%s/revisions" % base, headers=headers, params={"filter": "service=%s" % service_resource, "pageSize": 20}, timeout=8)
    if service_response.status_code >= 400 or revisions_response.status_code >= 400:
        return _runtime_release_fallback("Cloud Run control-plane read failed.")
    service_data = service_response.json()
    revisions = revisions_response.json().get("revisions") or []
    history = [{"revision": item.get("name", "").split("/")[-1], "created_at": item.get("createTime"), "updated_at": item.get("updateTime")} for item in revisions]
    traffic = service_data.get("trafficStatuses") or service_data.get("traffic")
    return {"status": "release-observed", "stage": "production", "service": service, "active_revision": os.getenv("K_REVISION") or service_data.get("latestReadyRevision"), "deployment_history": history, "traffic": traffic, "deployment_timestamp": history[0].get("created_at") if history else None, "authority": "cloud_run_admin_api"}


def _metadata_token() -> Optional[str]:
    try:
        response = requests.get("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"}, timeout=2)
        return str(response.json().get("access_token")) if response.status_code == 200 else None
    except requests.RequestException:
        return None


def _runtime_release_fallback(control_plane_error: str) -> Dict[str, Any]:
    revision = os.getenv("K_REVISION")
    service = os.getenv("K_SERVICE")
    if not revision:
        return {"status": "unknown", "unknown_reason": control_plane_error}
    history: List[Dict[str, Any]] = []
    try:
        from app.platform.github_execution.pr_lifecycle import _github_get
        runs = _github_get("/actions/workflows/platform-deploy.yml/runs", os.getenv("GITHUB_TOKEN") or "", params={"branch": "main", "per_page": 20})
        history = [{"workflow_run_id": item.get("id"), "head_sha": item.get("head_sha"), "status": item.get("status"), "conclusion": item.get("conclusion"), "created_at": item.get("created_at"), "updated_at": item.get("updated_at"), "url": item.get("html_url")} for item in runs.get("workflow_runs") or []]
    except Exception:
        history = []
    return {
        "status": "release-observed",
        "stage": "production",
        "service": service,
        "active_revision": revision,
        "deployment_history": history,
        "deployment_timestamp": history[0].get("updated_at") if history else os.getenv("SOURCE_COMMIT_TIMESTAMP"),
        "traffic": None,
        "authority": "cloud_run_runtime_and_github_actions",
        "control_plane_error": control_plane_error,
    }


def _workflow_state(db: Any, workflow_run_id: str) -> Dict[str, Any]:
    row = db.query(PlatformWorkflowStepRun).filter(
        PlatformWorkflowStepRun.workflow_run_id == workflow_run_id,
        PlatformWorkflowStepRun.step_id == "mission_run_state",
    ).first()
    output = _json_object(row.output_json) if row is not None else {}
    bridge = output.get("bridge_result") if isinstance(output.get("bridge_result"), dict) else {}
    return bridge.get("handler_result") if isinstance(bridge.get("handler_result"), dict) else {}


def _runtime_gates(stage: Optional[str], status: Optional[str]) -> List[Dict[str, Any]]:
    order = ("accepted", "context_analysis", "engineering_handoff", "change_set_generation", "change_set_ready", "mission_complete")
    current = str(stage or status or "accepted")
    if str(status) == "completed":
        return [{"name": name, "status": "completed"} for name in order]
    current_index = next((index for index, name in enumerate(order) if current.startswith(name)), 0)
    return [{"name": name, "status": "completed" if index < current_index or (current == "change_set_ready" and name != "mission_complete") or (str(status) == "completed" and name == "mission_complete") else "current" if index == current_index else "pending"} for index, name in enumerate(order)]


def _json_object(value: str) -> Dict[str, Any]:
    try:
        result = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None
