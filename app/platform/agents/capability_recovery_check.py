from __future__ import annotations

import argparse
import json

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.capability_recovery_service import (
    create_recovery_approvals_for_missing_capabilities,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create safe Agent Factory recovery approvals for missing required capabilities."
    )
    parser.add_argument(
        "--required-capability",
        action="append",
        required=True,
        help="Required capability to check. Can be passed multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect missing capabilities but do not create approvals.",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send newly created recovery approvals to Telegram.",
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
        result = create_recovery_approvals_for_missing_capabilities(
            db,
            required_capabilities=args.required_capability,
            create_approvals=not args.dry_run,
            send_telegram=args.send_telegram,
            log_event=not args.no_audit_log,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
