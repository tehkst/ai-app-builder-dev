from __future__ import annotations

import argparse
import json

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_dependency_graph_service import (
    DEFAULT_PLATFORM_REQUIRED_CAPABILITIES,
    build_agent_dependency_graph,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and inspect the agent capability dependency graph."
    )
    parser.add_argument(
        "--required-capability",
        action="append",
        default=None,
        help="Required capability to check. Can be passed multiple times.",
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
        required_capabilities = (
            args.required_capability
            if args.required_capability
            else DEFAULT_PLATFORM_REQUIRED_CAPABILITIES
        )

        result = build_agent_dependency_graph(
            db,
            required_capabilities=required_capabilities,
            log_event=not args.no_audit_log,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
