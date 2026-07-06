from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

SERVICE_NAME = "ai-software-factory-production"
REGION = "asia-southeast1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_runtime_deployment_plugin(goal: str, review_package: Dict[str, Any], requested_by: str = "founder") -> Dict[str, Any]:
    has_review_package = bool(review_package)
    ready = has_review_package and bool(review_package.get("head_branch"))
    return {
        "roadmap_item": "BR-EXEC-04",
        "name": "Deployment Runtime",
        "status": "deployment_package_ready" if ready else "blocked_pending_review_package",
        "goal": goal,
        "requested_by": requested_by,
        "created_at": _now(),
        "service": SERVICE_NAME,
        "region": REGION,
        "deployment_flow": [
            {"stage": "merge_detection", "status": "waiting_for_founder_merge", "owner": "founder"},
            {"stage": "platform_deploy", "status": "blocked_until_merge_verified", "owner": "mission_control"},
            {"stage": "revision_verification", "status": "blocked_until_deploy_complete", "owner": "mission_control"},
            {"stage": "smoke_tests", "status": "blocked_until_revision_live", "owner": "mission_control"},
            {"stage": "deployment_report", "status": "blocked_until_smoke_tests_complete", "owner": "mission_control"},
        ],
        "verification_targets": {
            "cloud_run_service": SERVICE_NAME,
            "cloud_run_region": REGION,
            "traffic_required_percent": 100,
            "expected_revision": None,
        },
        "smoke_tests": [
            {"name": "health", "path": "/health", "status": "pending"},
            {"name": "readiness", "path": "/health/readiness", "status": "pending"},
            {"name": "mission_runtime", "path": "/platform/mission-runtime/run", "status": "pending"},
            {"name": "board_room", "path": "Board Room UI", "status": "manual_check_pending"},
        ],
        "rollback_guidance": {
            "required_if": "health, readiness, or mission runtime smoke tests fail",
            "action": "shift traffic back to the previous stable Cloud Run revision",
            "requires_founder_approval": True,
        },
        "execution_policy": {
            "deploy_after_founder_merge": True,
            "auto_deploy_without_merge": False,
            "auto_rollback": False,
            "requires_founder_approval": True,
            "requires_smoke_tests": True,
        },
        "next_action": {
            "owner": "founder" if ready else "mission_control",
            "action": "Merge approved PR, then run deployment verification." if ready else "Complete BR-EXEC-03 review package first.",
        },
        "audit_trail": [
            {"event": "deployment_runtime_package_created", "timestamp": _now(), "actor": "deployment_runtime_plugin"},
            {"event": "manual_merge_gate_enforced", "timestamp": _now(), "actor": "governance"},
            {"event": "smoke_test_gate_required", "timestamp": _now(), "actor": "governance"},
        ],
    }
