from __future__ import annotations

import argparse
import json

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
    list_recent_workflow_runs,
)


def _compact_workflow_run_summary(detail: dict) -> dict:
    if not detail.get("found"):
        return detail

    steps = []
    for step in detail.get("steps") or []:
        handler_result = step.get("handler_result") or {}
        steps.append(
            {
                "step_id": step.get("step_id"),
                "title": step.get("title"),
                "status": step.get("status"),
                "required_capability": step.get("required_capability"),
                "selected_agent_id": step.get("selected_agent_id"),
                "requires_steps": step.get("requires_steps") or [],
                "handler_success": handler_result.get("success")
                if isinstance(handler_result, dict)
                else None,
                "handler_message": handler_result.get("message")
                if isinstance(handler_result, dict)
                else None,
            }
        )

    return {
        "success": detail.get("success"),
        "found": detail.get("found"),
        "summary": True,
        "workflow_run_id": detail.get("workflow_run_id"),
        "workflow_name": detail.get("workflow_name"),
        "status": detail.get("status"),
        "plan_status": detail.get("plan_status"),
        "simulation": detail.get("simulation"),
        "step_count": detail.get("step_count"),
        "completed_step_count": detail.get("completed_step_count"),
        "blocked_step_count": detail.get("blocked_step_count"),
        "failed_step_count": detail.get("failed_step_count"),
        "missing_capability_count": len(detail.get("missing_capabilities") or []),
        "dependency_repair_count": len(detail.get("dependency_repair_plan") or []),
        "created_at": detail.get("created_at"),
        "completed_at": detail.get("completed_at"),
        "steps": steps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a persisted workflow run by workflow_run_id."
    )
    parser.add_argument(
        "workflow_run_id",
        nargs="?",
        help="Workflow run id to inspect. Omit this with --recent to list recent runs.",
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="List recent workflow runs instead of inspecting one run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Recent workflow run limit when using --recent.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Return a compact workflow run summary instead of full details.",
    )
    args = parser.parse_args()

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        if args.recent:
            result = {
                "success": True,
                "recent": True,
                "workflow_runs": list_recent_workflow_runs(db, limit=args.limit),
            }
        else:
            if not args.workflow_run_id:
                raise ValueError("workflow_run_id is required unless --recent is used")
            result = get_workflow_run_detail(
                db,
                workflow_run_id=args.workflow_run_id,
            )
            if args.summary:
                result = _compact_workflow_run_summary(result)

        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
