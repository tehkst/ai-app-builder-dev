from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_workflow_executor_service import execute_agent_workflow
from app.platform.services.app_build_workflow_generator_service import (
    generate_app_build_workflow,
)
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
)


def run_app_build_request(
    *,
    app_request: str,
    workflow_name: str | None = None,
    real_bridge: bool = False,
) -> Dict[str, Any]:
    generated_workflow = generate_app_build_workflow(
        app_request=app_request,
        workflow_name=workflow_name,
    )

    create_platform_tables()
    register_builtin_agents()
    register_specialist_agents()

    db = PlatformSessionLocal()
    generated_file_persistence: Dict[str, Any] = {
        "persisted": False,
        "generated_file_count": 0,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
    }
    try:
        execution_result = execute_agent_workflow(
            db,
            workflow_name=generated_workflow["workflow_name"],
            steps=generated_workflow["steps"],
            simulation=not real_bridge,
        )
        workflow_run_id = execution_result.get("workflow_run_id")
        if workflow_run_id:
            workflow_detail = get_workflow_run_detail(db, workflow_run_id=str(workflow_run_id))
            generated_file_persistence = persist_generated_files_for_workflow(
                db,
                workflow_detail,
            )
    finally:
        db.close()

    return {
        "success": execution_result.get("success") is True,
        "status": execution_result.get("status"),
        "generated_workflow": True,
        "workflow_version": generated_workflow.get("workflow_version"),
        "workflow_name": generated_workflow.get("workflow_name"),
        "app_request": generated_workflow.get("app_request"),
        "generated_step_count": generated_workflow.get("step_count"),
        "execution": execution_result,
        "summary": {
            "plan_status": execution_result.get("plan_status"),
            "step_count": execution_result.get("step_count"),
            "completed_step_count": execution_result.get("completed_step_count"),
            "blocked_step_count": execution_result.get("blocked_step_count"),
            "failed_step_count": execution_result.get("failed_step_count"),
            "workflow_run_id": execution_result.get("workflow_run_id"),
            "persisted": (execution_result.get("persistence") or {}).get("persisted"),
            "generated_file_count": generated_file_persistence.get("generated_file_count"),
            "generated_file_persistence": generated_file_persistence,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and run a safe app-build workflow from a user app request."
    )
    parser.add_argument(
        "app_request",
        help="User app request, for example: 'Build me a booking app for yoga classes'.",
    )
    parser.add_argument(
        "--workflow-name",
        help="Optional workflow name override.",
    )
    parser.add_argument(
        "--real-bridge",
        action="store_true",
        help="Execute through the real agent bridge instead of simulation mode.",
    )
    args = parser.parse_args()

    result = run_app_build_request(
        app_request=args.app_request,
        workflow_name=args.workflow_name,
        real_bridge=args.real_bridge,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
