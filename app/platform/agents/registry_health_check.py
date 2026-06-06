from __future__ import annotations

import argparse
import json

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_registry_health_service import (
    check_and_repair_agent_registry,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check and optionally repair the Agent Registry from persisted agent definitions."
    )
    parser.add_argument(
        "--no-repair",
        action="store_true",
        help="Only check health. Do not repair missing persisted agents.",
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
        result = check_and_repair_agent_registry(
            db,
            repair=not args.no_repair,
            log_event=not args.no_audit_log,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
