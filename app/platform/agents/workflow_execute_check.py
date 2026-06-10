from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_workflow_executor_service import execute_agent_workflow


def _default_steps() -> List[Dict[str, Any]]:
    return [
        {
            "step_id": "architecture",
            "title": "Create Application Architecture Plan",
            "required_capability": "architect_task",
            "requires_steps": [],
        },
        {
            "step_id": "builder",
            "title": "Create Safe Implementation Plan",
            "required_capability": "builder_task",
            "requires_steps": ["architecture"],
        },
        {
            "step_id": "review",
            "title": "Review Implementation Plan",
            "required_capability": "reviewer_task",
            "requires_steps": ["builder"],
        },
        {
            "step_id": "test",
            "title": "Create Validation Plan",
            "required_capability": "test_task",
            "requires_steps": ["review"],
        },
    ]


def _load_steps(path: Optional[str]) -> List[Dict[str, Any]]:
    if not path:
        return _default_steps()

    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get("steps", [])

    if not isinstance(data, list):
        raise ValueError("Workflow input must be a list of steps or an object with a steps list.")

    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute an agent workflow in safe simulation mode."
    )
    parser.add_argument(
        "--steps-file",
        help="Optional JSON file containing workflow execution steps.",
    )
    parser.add_argument(
        "--workflow-name",
        default="Agent Workflow",
        help="Human-readable workflow name.",
    )
    parser.add_argument(
        "--no-audit-log",
        action="store_true",
        help="Do not write a platform audit event.",
    )
    parser.add_argument(
        "--real-bridge",
        action="store_true",
        help="Execute ready steps through the safe agent execution bridge instead of simulation.",
    )
    args = parser.parse_args()

    create_platform_tables()
    register_builtin_agents()
    register_specialist_agents()

    db = PlatformSessionLocal()
    try:
        result = execute_agent_workflow(
            db,
            steps=_load_steps(args.steps_file),
            workflow_name=args.workflow_name,
            simulation=not args.real_bridge,
            log_event=not args.no_audit_log,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
