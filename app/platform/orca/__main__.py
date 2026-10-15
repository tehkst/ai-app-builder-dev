"""Command line for Orca missions.

    python -m app.platform.orca start --goal "Add a /health endpoint" --workspace /tmp/ai-software-factory/workspaces/demo
    python -m app.platform.orca run ORCA-XXXXXXXXXXXX
    python -m app.platform.orca approve ORCA-XXXXXXXXXXXX      # allow running generated code for this mission
    python -m app.platform.orca decline ORCA-XXXXXXXXXXXX
    python -m app.platform.orca retry ORCA-XXXXXXXXXXXX        # give an escalated task another round
    python -m app.platform.orca status ORCA-XXXXXXXXXXXX
    python -m app.platform.orca list
"""
from __future__ import annotations

import argparse
import json
import sys

from app.platform.orca.engine import Orca
from app.platform.orca.models import Mission


def _summary(mission: Mission) -> dict:
    return {
        "mission_id": mission.mission_id, "status": mission.status, "goal": mission.goal,
        "execution_approval": mission.execution_approval, "plan_summary": mission.plan_summary,
        "tasks": [{"id": t.task_id, "title": t.title, "status": t.status, "attempts": t.attempts}
                  for t in mission.tasks],
        "escalation": (mission.escalation or {}).get("reason"),
        "paused_reason": mission.paused_reason,
        "last_event": mission.events[-1] if mission.events else None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.platform.orca")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="create a mission and run it until it pauses or finishes")
    start.add_argument("--goal", required=True)
    start.add_argument("--workspace", required=True)
    start.add_argument("--approve-execution", action="store_true",
                       help="founder pre-approves running generated code for this mission")
    for name in ("run", "approve", "decline", "retry", "status"):
        commands.add_parser(name).add_argument("mission_id")
    commands.add_parser("list")
    args = parser.parse_args(argv)

    try:
        return _dispatch(args)
    except ValueError as exc:
        print(f"orca: {exc}", file=sys.stderr)
        return 2


def _dispatch(args) -> int:
    orca = Orca()
    if args.command == "list":
        print(json.dumps(orca.store.list_ids(), indent=2))
        return 0
    if args.command == "start":
        mission = orca.start_mission(args.goal, args.workspace, execution_approved=args.approve_execution)
        mission = orca.run(mission.mission_id)
    elif args.command in ("approve", "decline"):
        orca.decide_execution(args.mission_id, approved=args.command == "approve")
        mission = orca.run(args.mission_id)
    elif args.command == "retry":
        orca.retry_task(args.mission_id)
        mission = orca.run(args.mission_id)
    elif args.command == "run":
        mission = orca.run(args.mission_id)
    else:
        mission = orca.store.load(args.mission_id)
        if mission is None:
            print(f"Mission {args.mission_id} not found.", file=sys.stderr)
            return 1
    print(json.dumps(_summary(mission), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
