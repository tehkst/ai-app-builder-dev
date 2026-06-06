from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_execution_bridge_service import execute_agent_via_bridge


def _sample_step_run(agent_id: str, capability: str) -> Dict[str, Any]:
    return {
        "step_run_id": "step_run_bridge_check",
        "step_id": "bridge_check",
        "title": "Bridge Check Step",
        "required_capability": capability,
        "requires_steps": [],
        "candidate_agents": [
            {
                "agent_id": agent_id,
                "name": agent_id,
            }
        ],
        "selected_agent": {
            "agent_id": agent_id,
            "name": agent_id,
        },
        "agent_available": True,
        "status": "running",
        "output": None,
        "error": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a safe agent execution bridge check."
    )
    parser.add_argument(
        "--agent-id",
        default="test_agent",
        help="Registered agent ID to execute through the safe bridge.",
    )
    parser.add_argument(
        "--capability",
        default="test_task",
        help="Capability required by the step.",
    )
    parser.add_argument(
        "--workflow-run-id",
        default="workflow_run_bridge_check",
        help="Workflow run ID to include in the task payload.",
    )
    parser.add_argument(
        "--no-audit-log",
        action="store_true",
        help="Do not write a platform audit event.",
    )
    args = parser.parse_args()

    create_platform_tables()
    register_builtin_agents()
    register_specialist_agents()

    db = PlatformSessionLocal()
    try:
        result = execute_agent_via_bridge(
            db,
            workflow_run_id=args.workflow_run_id,
            step_run=_sample_step_run(args.agent_id, args.capability),
            workflow_context={
                "source": "agent_bridge_check",
                "mode": "safe",
            },
            safe_mode=True,
            log_event=not args.no_audit_log,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
