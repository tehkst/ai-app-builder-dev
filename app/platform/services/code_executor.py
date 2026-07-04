from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.senior_software_engineer import create_implementation_package


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "mission"


def _branch_name(goal: str) -> str:
    return f"mission-control/{_slug(goal)}"


def _execution_steps(package: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = [
        {
            "step": 1,
            "name": "Create execution branch",
            "action": "create_branch",
            "status": "blocked_pending_founder_approval",
            "requires_approval": True,
        },
        {
            "step": 2,
            "name": "Apply proposed file changes",
            "action": "apply_patch_instructions",
            "status": "blocked_pending_founder_approval",
            "requires_approval": True,
        },
    ]
    for index, patch in enumerate(package.get("proposed_patches", []), start=1):
        steps.append(
            {
                "step": len(steps) + 1,
                "name": f"Patch {patch.get('path')}",
                "action": patch.get("patch_type", "patch_file"),
                "path": patch.get("path"),
                "instructions": patch.get("instructions", []),
                "status": "planned",
                "requires_approval": True,
            }
        )
    steps.extend(
        [
            {
                "step": len(steps) + 1,
                "name": "Run validation checks",
                "action": "validate",
                "status": "planned",
                "requires_approval": True,
            },
            {
                "step": len(steps) + 2,
                "name": "Prepare commit",
                "action": "commit",
                "status": "blocked_pending_founder_approval",
                "requires_approval": True,
            },
            {
                "step": len(steps) + 3,
                "name": "Prepare pull request",
                "action": "open_pull_request",
                "status": "blocked_pending_founder_approval",
                "requires_approval": True,
            },
        ]
    )
    return steps


def _validation_gates(package: Dict[str, Any]) -> List[Dict[str, str]]:
    gates = [
        {"gate": "founder_approval", "status": "required", "description": "Founder must approve before repository writes."},
        {"gate": "protected_boundary", "status": "required", "description": "No auth, login, session, or deployment config changes unless explicitly scoped."},
        {"gate": "human_review", "status": "required", "description": "Human review is required before merge."},
    ]
    for check in package.get("validation_checks", []):
        gates.append(
            {
                "gate": check.get("name", "validation"),
                "status": "planned",
                "description": check.get("expected", "Validation must pass."),
            }
        )
    return gates


def create_code_execution_plan(*, goal: str, db: Optional[Session] = None, scope: str = "mission_control") -> Dict[str, Any]:
    package = create_implementation_package(goal=goal, db=db, scope=scope)
    branch = _branch_name(goal)
    return {
        "mode": "autonomous_code_executor_v1",
        "scope": scope,
        "goal": goal,
        "implementation_package": package,
        "repository_intent": {
            "target_repository": "tehkst/ai-app-builder-dev",
            "base_branch": "main",
            "proposed_branch": branch,
            "commit_message": package.get("commit_message"),
            "pr_title": package.get("commit_message"),
            "pr_body": package.get("pr_body"),
        },
        "execution_steps": _execution_steps(package),
        "validation_gates": _validation_gates(package),
        "rollback_plan": [
            "If validation fails before PR creation, discard the generated branch.",
            "If PR validation fails, close the PR and keep the branch for inspection.",
            "If production regresses after merge and deploy, shift Cloud Run traffic to the previous known-good revision.",
        ],
        "executor_policy": {
            "safe_to_execute": False,
            "safe_to_write_files": False,
            "safe_to_commit": False,
            "safe_to_open_pr": False,
            "requires_founder_approval": True,
            "requires_human_review": True,
            "reason": "Code Executor v1 prepares a governed execution plan only. Repository write actions remain disabled until explicit executor governance is implemented.",
        },
    }


def format_code_execution_plan_markdown(plan: Dict[str, Any]) -> str:
    lines: List[str] = [
        "## Autonomous Code Executor v1",
        "",
        f"**Goal:** {plan.get('goal', '')}",
        f"**Branch:** {plan.get('repository_intent', {}).get('proposed_branch', '')}",
        "",
        "### Execution Steps",
    ]
    for step in plan.get("execution_steps", []):
        lines.append(f"- {step['step']}. {step['name']} — {step['status']}")
    lines.extend(["", "### Validation Gates"])
    for gate in plan.get("validation_gates", []):
        lines.append(f"- {gate['gate']}: {gate['status']} — {gate['description']}")
    lines.extend(["", "### Executor Policy"])
    policy = plan.get("executor_policy", {})
    lines.append(f"- safe_to_execute: {policy.get('safe_to_execute')}")
    lines.append(f"- safe_to_commit: {policy.get('safe_to_commit')}")
    lines.append(f"- safe_to_open_pr: {policy.get('safe_to_open_pr')}")
    lines.append(f"- reason: {policy.get('reason')}")
    return "\n".join(lines)
