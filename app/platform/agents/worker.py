from __future__ import annotations

import argparse
import os
import threading
import time
import uuid
from typing import Any, Dict, Optional

from app.platform.agents import builtin  # noqa: F401 - registers built-in agents
from app.platform.agents import specialists  # noqa: F401 - registers specialist agents
from app.platform.operating_console import mission_runtime_agent  # noqa: F401 - registers durable mission stage agent
from app.platform.agents.registry import choose_agent_for_task, get_agent, list_agents
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.agent_task_service import (
    claim_next_agent_task,
    claim_next_agent_task_for_parent,
    finalize_claimed_agent_task,
    renew_agent_task_lease,
)


LEASE_RENEWAL_SECONDS = 30.0
_ACTIVATION_LOCK = threading.Lock()
_ACTIVE_LOOPS: set[str] = set()


def execute_one_task(
    *,
    assigned_agent: str,
    task_type: Optional[str] = None,
    parent_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    db = PlatformSessionLocal()
    try:
        if parent_task_id:
            claimed = claim_next_agent_task_for_parent(
                db=db,
                assigned_agent=assigned_agent,
                parent_task_id=parent_task_id,
                task_type=task_type,
            )
        else:
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
            finalize_claimed_agent_task(
                db=db, task_id=task["task_id"], lease_owner=assigned_agent, status="failed",
                error_message=f"No registered agent can execute task_type={task.get('task_type')}",
            )
            return {
                "executed": False,
                "reason": "no_registered_agent",
                "task": task,
            }

        stop_renewal = threading.Event()
        lease_lost = threading.Event()
        renewal = threading.Thread(
            target=_renew_lease_until_stopped,
            args=(task["task_id"], assigned_agent, stop_renewal, lease_lost),
            name=f"lease-{task['task_id']}",
            daemon=True,
        )
        renewal.start()
        try:
            if agent.agent_id == "orchestrator_agent":
                from app.platform.agents.orchestrator import create_child_tasks_for_goal

                result = create_child_tasks_for_goal(db=db, parent_task=task)
            else:
                result = agent.handler(task)
        except Exception as exc:
            result = {"success": False, "error": f"Agent handler failed: {type(exc).__name__}"}
        finally:
            stop_renewal.set()
            renewal.join(timeout=LEASE_RENEWAL_SECONDS + 1)

        if lease_lost.is_set():
            return {"executed": True, "status": "lease_lost", "task_id": task["task_id"], "agent_id": agent.agent_id}

        if result.get("success") is False:
            finalized = finalize_claimed_agent_task(
                db=db, task_id=task["task_id"], lease_owner=assigned_agent, status="failed",
                result_payload=result, error_message=result.get("error") or "Agent execution failed",
            )
            return {
                "executed": True,
                "status": "failed" if finalized else "lease_lost",
                "task_id": task["task_id"],
                "agent_id": agent.agent_id,
                "result": result,
            }

        updated = finalize_claimed_agent_task(
            db=db, task_id=task["task_id"], lease_owner=assigned_agent,
            status="completed", result_payload=result,
        )
        if not updated:
            return {"executed": True, "status": "lease_lost", "task_id": task["task_id"], "agent_id": agent.agent_id}

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


def _renew_lease_until_stopped(task_id: str, owner: str, stop: threading.Event, lease_lost: threading.Event) -> None:
    while not stop.wait(LEASE_RENEWAL_SECONDS):
        db = PlatformSessionLocal()
        try:
            if not renew_agent_task_lease(db, task_id=task_id, lease_owner=owner):
                lease_lost.set()
                return
        finally:
            db.close()


def ensure_agent_worker_running(*, task_type: Optional[str] = None) -> None:
    key = task_type or "*"
    with _ACTIVATION_LOCK:
        if key in _ACTIVE_LOOPS:
            return
        _ACTIVE_LOOPS.add(key)
    threading.Thread(target=_run_until_idle, args=(key, task_type), name=f"agent-worker-{key}", daemon=True).start()


def _run_until_idle(key: str, task_type: Optional[str]) -> None:
    owner = f"agent-worker-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    try:
        while execute_one_task(assigned_agent=owner, task_type=task_type).get("executed"):
            pass
    finally:
        with _ACTIVATION_LOCK:
            _ACTIVE_LOOPS.discard(key)


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
