from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_execution_planner_service import build_agent_execution_plan


def _default_steps() -> List[Dict[str, Any]]:
    return [
        {
            "step_id": "architecture",
            "title": "Create Application Architecture",
            "required_capability": "architecture_task",
            "requires_steps": [],
        },
        {
            "step_id": "implementation",
            "title": "Build Application Files",
            "required_capability": "code_generation_task",
            "requires_steps": ["architecture"],
        },
        {
            "step_id": "payment",
            "title": "Implement Payment Integration",
            "required_capability": "payment_integration_task",
            "requires_steps": ["implementation"],
        },
        {
            "step_id": "reporting",
            "title": "Implement Reporting",
            "required_capability": "reporting_task",
            "requires_steps": ["implementation"],
        },
        {
            "step_id": "review",
            "title": "Review Generated Application",
            "required_capability": "review_task",
            "requires_steps": ["implementation", "payment", "reporting"],
        },
        {
            "step_id": "test",
            "title": "Test Generated Application",
            "required_capability": "test_task",
            "requires_steps": ["review"],
        },
    ]


def _load_steps(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        return _default_steps()

    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get("steps", [])

    if not isinstance(data, list):
        raise ValueError("Execution plan input must be a list of steps or an object with a steps list.")

    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an agent execution dependency plan."
    )
    parser.add_argument(
        "--steps-file",
        help="Optional JSON file containing execution steps.",
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
        result = build_agent_execution_plan(
            db,
            steps=_load_steps(args.steps_file),
            log_event=not args.no_audit_log,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
