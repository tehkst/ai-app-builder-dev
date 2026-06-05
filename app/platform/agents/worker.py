from __future__ import annotations

import argparse
import time
from typing import Any, Dict, Optional

from app.platform.agents import builtin  # noqa: F401 - registers built-in agents
from app.platform.agents.registry import choose_agent_for_task, get_agent, list_agents
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.agent_task_service import (
    claim_next_agent_task,
    update_agent_task_status,
)


def execute_one_task(
    *,
    assigned_agent: str,
    task_type: Optional[str] = None,
) -> Dict[str, Any]:
    db = PlatformSessionLocal()
    try:
        claimed = claim_next_agent_task(
            db=db,
            assigned_agent=assigned_agent,
            task_type=task_type,
        )
        if not claimed:
            task = None
        elif isinstance(claimed, dict) and "task" in claimed:
            task = claimed.get("task")
        else:
            task = claimed

        if not task:
            return {
                "executed": False,
                "reason": "no_queued_task",
                "available_agents": list_agents(),
            }

        agent = get_agent(assigned_agent)
        if not agent:
            agent = choose_agent_for_task(task.get("task_type", ""))

        if not agent:
            update_agent_task_status(
                db=db,
                task_id=task["task_id"],
                status="failed",
                error_message=f"No registered agent can execute task_type={task.get('task_type')}",
            )
            return {
                "executed": False,
                "reason": "no_registered_agent",
                "task": task,
            }

        result = agent.handler(task)

        if result.get("success") is False:
            update_agent_task_status(
                db=db,
                task_id=task["task_id"],
                status="failed",
                result_payload=result,
                error_message=result.get("error") or "Agent execution failed",
            )
            return {
                "executed": True,
                "status": "failed",
                "task_id": task["task_id"],
                "agent_id": agent.agent_id,
                "result": result,
            }

        updated = update_agent_task_status(
            db=db,
            task_id=task["task_id"],
            status="completed",
            result_payload=result,
        )

        return {
            "executed": True,
            "status": "completed",
            "task_id": task["task_id"],
            "agent_id": agent.agent_id,
            "task": updated,
            "result": result,
        }
    finally:
        db.close()


def run_loop(
    *,
    assigned_agent: str,
    task_type: Optional[str],
    once: bool,
    sleep_seconds: float,
) -> None:
    while True:
        result = execute_one_task(
            assigned_agent=assigned_agent,
            task_type=task_type,
        )
        print(result)

        if once:
            return

        time.sleep(sleep_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Software Factory agent worker loop.")
    parser.add_argument("--agent", default="test_agent", help="Agent ID to run as.")
    parser.add_argument("--task-type", default=None, help="Optional task type filter.")
    parser.add_argument("--once", action="store_true", help="Execute at most one task then exit.")
    parser.add_argument("--sleep", type=float, default=5.0, help="Sleep seconds between loop attempts.")
    args = parser.parse_args()

    run_loop(
        assigned_agent=args.agent,
        task_type=args.task_type,
        once=args.once,
        sleep_seconds=args.sleep,
    )


if __name__ == "__main__":
    main()
