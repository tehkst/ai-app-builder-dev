from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_runtime_repository_plugin(goal: str, outputs: Dict[str, Any], requested_by: str = "founder") -> Dict[str, Any]:
    package = outputs.get("implementation_package", {})
    patches = package.get("proposed_patches", []) or []
    return {
        "roadmap_item": "BR-EXEC-02",
        "name": "Repository Execution Engine",
        "status": "review_package_ready" if patches else "waiting_for_implementation_package",
        "goal": goal,
        "requested_by": requested_by,
        "created_at": _now(),
        "repository": "tehkst/ai-app-builder-dev",
        "base_branch": "main",
        "proposed_branch": "mission-control/" + "".join(ch.lower() if ch.isalnum() else "-" for ch in goal).strip("-")[:56],
        "edit_operations": [
            {
                "id": f"edit-{index}",
                "path": item.get("path") or item.get("file") or f"unspecified-{index}",
                "operation": item.get("operation") or item.get("patch_type") or "modify",
                "instructions": item.get("instructions") or item.get("changes") or [],
                "status": "ready_for_review",
            }
            for index, item in enumerate(patches, start=1)
        ],
        "review_package": {
            "commit_message": f"BR-EXEC-02 {goal[:72]}",
            "pull_request_title": f"Mission Control: {goal[:90]}",
            "requires_founder_review": True,
            "auto_merge": False,
            "auto_deploy": False,
        },
    }
