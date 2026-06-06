from __future__ import annotations

import argparse
import json

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
    list_recent_workflow_runs,
)


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

        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
