# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from app.platform.agents.approval_gated_static_preview_materialization_check import (
    run_check as run_v90_materialization_check,
)
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.materialization_approval_record_service import (
    create_materialization_approval_record,
)
from app.platform.services.materialization_execution_gate_service import (
    attempt_materialization_execution,
)

def main() -> None:
    parser = argparse.ArgumentParser(description="V91 static preview browser smoke check.")
    parser.add_argument("app_request", nargs="?", default="Build me a simple booking app for yoga classes")
    parser.add_argument("--simulation", action="store_true")
    args = parser.parse_args()

    result = run_static_preview_browser_smoke_check(
        app_request=args.app_request,
        real_bridge=not args.simulation,
    )
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result.get("success"):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
