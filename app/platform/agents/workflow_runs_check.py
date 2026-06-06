from __future__ import annotations

import argparse
import json

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.workflow_run_persistence_service import list_recent_workflow_runs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List recent persisted workflow runs."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of workflow runs to list.",
    )
    args = parser.parse_args()

    create_platform_tables()

    db = PlatformSessionLocal()
    try:
        result = {
            "workflow_runs": list_recent_workflow_runs(
                db,
                limit=args.limit,
            )
        }
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
