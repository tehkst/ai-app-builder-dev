# Split from the legacy module to keep each Python file under 200 lines.
import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
ROOT = Path(__file__).resolve().parents[3]
SOURCE_GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"

def execute_plan(plan_path: Path, approved: bool, sandbox: bool) -> Dict:
    plan = load_plan(plan_path)
    validation_errors = validate_approval_boundary(
        plan=plan,
        approved=approved,
        sandbox=sandbox,
    )

    if validation_errors:
        return {
            "passed": False,
            "executed": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "plan_path": str(plan_path),
            "plan_source": plan.get("source"),
            "validation_errors": validation_errors,
        }

    sandbox_app = copy_generated_app_to_sandbox()

    try:
        seeded_files = seed_sandbox_from_plan(sandbox_app, plan)
        actions = execute_sandbox_repairs(sandbox_app, plan)

        successful_actions = [
            action
            for action in actions
            if action.get("action") == "deleted_from_sandbox"
        ]

        return {
            "passed": bool(successful_actions),
            "executed": bool(successful_actions),
            "sandbox_mode": True,
            "auto_edit_real_project": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "plan_path": str(plan_path),
            "plan_source": plan.get("source"),
            "sandbox_app": str(sandbox_app),
            "seeded_files": seeded_files,
            "actions": actions,
            "successful_action_count": len(successful_actions),
            "sandbox_deleted": True,
        }
    finally:
        cleanup_sandbox(sandbox_app)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute an approved self-healing repair plan safely."
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to repair plan JSON.",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Explicit approval required before executing any repair action.",
    )
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="Execute only against a temporary sandbox copy.",
    )

    args = parser.parse_args()

    report = execute_plan(
        plan_path=Path(args.plan),
        approved=args.approve,
        sandbox=args.sandbox,
    )

    print(json.dumps(report, indent=2))

    if not report["passed"]:
        print("SELF-HEALING REPAIR EXECUTION REFUSED")
        raise SystemExit(1)

    print("SELF-HEALING REPAIR EXECUTION PASSED")

if __name__ == "__main__":
    main()
