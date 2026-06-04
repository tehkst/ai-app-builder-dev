import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[3]
SOURCE_GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"


def load_plan(plan_path: Path) -> Dict:
    if not plan_path.exists():
        raise FileNotFoundError(f"Repair plan not found: {plan_path}")

    return json.loads(plan_path.read_text())


def validate_approval_boundary(plan: Dict, approved: bool, sandbox: bool) -> List[str]:
    errors = []

    if not approved:
        errors.append("Execution requires explicit --approve flag.")

    if not sandbox:
        errors.append("Only sandbox execution is supported in this version.")

    if not plan.get("repair_needed", False):
        errors.append("Plan does not require repair.")

    if plan.get("risk_level") != "low":
        errors.append("Only low-risk plans can be executed by this version.")

    if not plan.get("auto_fix_available", False):
        errors.append("Plan does not allow automatic fixing.")

    if not plan.get("requires_human_approval", True):
        errors.append("Plan approval metadata is invalid.")

    if not plan.get("simulation_mode", False):
        errors.append("Only simulation-mode plans can be executed by this version.")

    approval_boundary = plan.get("approval_boundary", {})

    if approval_boundary.get("can_modify_real_project_files", True):
        errors.append("Plan boundary allows real project modification, which is not supported.")

    if approval_boundary.get("can_delete_files", True):
        errors.append("Plan boundary allows file deletion outside sandbox, which is not supported.")

    return errors


def copy_generated_app_to_sandbox() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="repair-execution-"))
    sandbox_app = temp_dir / SOURCE_GENERATED_APP.name

    shutil.copytree(SOURCE_GENERATED_APP, sandbox_app)

    return sandbox_app


def seed_sandbox_from_plan(sandbox_app: Path, plan: Dict) -> List[Dict]:
    seeded = []

    for affected_file in plan.get("affected_files", []):
        if affected_file.get("issue_type") != "unexpected_file":
            continue

        target = sandbox_app / affected_file["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "This file was seeded into the sandbox to test approval-safe repair execution.\n"
        )

        seeded.append(
            {
                "path": affected_file["path"],
                "action": "seeded_unexpected_file",
                "exists_after_seed": target.exists(),
            }
        )

    return seeded


def execute_sandbox_repairs(sandbox_app: Path, plan: Dict) -> List[Dict]:
    actions = []

    for affected_file in plan.get("affected_files", []):
        issue_type = affected_file.get("issue_type")
        relative_path = affected_file.get("path")

        if issue_type != "unexpected_file":
            actions.append(
                {
                    "path": relative_path,
                    "issue_type": issue_type,
                    "action": "skipped",
                    "reason": "Only unexpected_file auto-fix is supported in this version.",
                }
            )
            continue

        target = sandbox_app / relative_path

        if not target.exists():
            actions.append(
                {
                    "path": relative_path,
                    "issue_type": issue_type,
                    "action": "skipped",
                    "reason": "Unexpected file was not present in sandbox.",
                }
            )
            continue

        target.unlink()

        actions.append(
            {
                "path": relative_path,
                "issue_type": issue_type,
                "action": "deleted_from_sandbox",
                "exists_after_action": target.exists(),
            }
        )

    return actions


def cleanup_sandbox(sandbox_app: Path) -> None:
    shutil.rmtree(sandbox_app.parent, ignore_errors=True)


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
            "validation_errors": validation_errors,
        }

    sandbox_app = copy_generated_app_to_sandbox()

    try:
        seeded_files = seed_sandbox_from_plan(sandbox_app, plan)
        actions = execute_sandbox_repairs(sandbox_app, plan)

        return {
            "passed": True,
            "executed": True,
            "sandbox_mode": True,
            "auto_edit_real_project": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "plan_path": str(plan_path),
            "sandbox_app": str(sandbox_app),
            "seeded_files": seeded_files,
            "actions": actions,
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
