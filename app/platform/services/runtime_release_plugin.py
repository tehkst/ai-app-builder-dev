from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

SERVICE_NAME = "ai-software-factory-production"
REGION = "asia-southeast1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_runtime_release_plugin(goal: str, review_package: Dict[str, Any], requested_by: str = "founder") -> Dict[str, Any]:
    ready = bool(review_package and review_package.get("head_branch"))
    return {
        "roadmap_item": "BR-EXEC-04",
        "name": "Deployment Runtime",
        "status": "release_package_ready" if ready else "blocked_pending_review_package",
        "goal": goal,
        "requested_by": requested_by,
        "created_at": _now(),
        "service": SERVICE_NAME,
        "region": REGION,
        "release_flow": [
            {"stage": "merge_check", "status": "waiting_for_founder_merge"},
            {"stage": "platform_release", "status": "blocked_until_merge_check"},
            {"stage": "revision_check", "status": "blocked_until_release_complete"},
            {"stage": "smoke_checks", "status": "blocked_until_revision_live"},
            {"stage": "release_report", "status": "blocked_until_checks_complete"},
        ],
        "verification_targets": {
            "cloud_run_service": SERVICE_NAME,
            "cloud_run_region": REGION,
            "traffic_required_percent": 100,
            "expected_revision": None,
        },
        "smoke_checks": [
            {"name": "health", "path": "/health", "status": "pending"},
            {"name": "readiness", "path": "/health/readiness", "status": "pending"},
            {"name": "mission_runtime", "path": "/platform/mission-runtime/run", "status": "pending"},
            {"name": "board_room", "path": "Board Room UI", "status": "manual_check_pending"},
        ],
        "rollback_guidance": {
            "required_if": "health, readiness, or mission runtime checks fail",
            "action": "shift traffic back to the previous stable Cloud Run revision",
            "requires_founder_approval": True,
        },
        "execution_policy": {
            "release_after_founder_merge": True,
            "auto_release_without_merge": False,
            "auto_rollback": False,
            "requires_founder_approval": True,
            "requires_smoke_checks": True,
        },
        "next_action": {
            "owner": "founder" if ready else "mission_control",
            "action": "Merge approved PR, then run release verification." if ready else "Complete BR-EXEC-03 review package first.",
        },
        "audit_trail": [
            {"event": "release_runtime_package_created", "timestamp": _now(), "actor": "release_runtime_plugin"},
            {"event": "manual_merge_gate_enforced", "timestamp": _now(), "actor": "governance"},
            {"event": "smoke_check_gate_required", "timestamp": _now(), "actor": "governance"},
        ],
    }
