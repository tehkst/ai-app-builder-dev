from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.engineering_manager import create_engineering_spec


def _trim(text: str, limit: int = 1200) -> str:
    return (text or "").strip()[:limit]


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "mission"


def _module_name(goal: str) -> str:
    return _slug(goal).replace("-", "_")


def _patch_plan_from_spec(goal: str, engineering_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    module = _module_name(goal)
    patches: List[Dict[str, Any]] = []
    for item in engineering_spec.get("file_change_map", []):
        original_path = item.get("path", "")
        if "services/" in original_path:
            path = f"app/platform/services/{module}.py"
            patch_type = "add_service_module"
            instructions = [
                "Create an isolated service module for the requested mission.",
                "Expose one pure function that accepts a dictionary payload and returns a structured dictionary response.",
                "Return mode, scope, goal, result, and execution_policy fields.",
                "Keep write execution disabled unless a future governance milestone enables it.",
            ]
        elif "api/" in original_path:
            path = f"app/platform/api/{module}_api.py"
            patch_type = "add_api_router"
            instructions = [
                "Create an additive FastAPI router for the mission.",
                "Define a Pydantic request model with optional token, goal, and scope fields.",
                "Expose a POST endpoint that calls the service module and returns structured output.",
                "Do not replace or modify existing Board Room chat routes.",
            ]
        elif original_path == "app/main.py":
            path = "app/main.py"
            patch_type = "register_router"
            instructions = [
                f"Import the new router from app.platform.api.{module}_api.",
                "Register the router near the existing platform routers.",
                "Do not remove or reorder auth, platform auth, or health routes.",
            ]
        else:
            path = original_path or f"docs/{_slug(goal)}-implementation.md"
            patch_type = "implementation_note"
            instructions = [item.get("purpose", "Document the required implementation change.")]
        patches.append(
            {
                "path": path,
                "change_type": item.get("change_type", "modify"),
                "patch_type": patch_type,
                "owner": item.get("owner", "Senior Software Engineer"),
                "purpose": item.get("purpose", "Implement mission requirement."),
                "instructions": instructions,
                "diff_hint": " | ".join(instructions),
            }
        )
    return patches


def _validation_checks(engineering_spec: Dict[str, Any]) -> List[Dict[str, str]]:
    checks: List[Dict[str, str]] = []
    for test in engineering_spec.get("test_plan", []):
        checks.append(
            {
                "type": test.get("type", "manual"),
                "name": test.get("name", "Validation check"),
                "command": test.get("command", "Manual verification"),
                "expected": test.get("expected", "Expected behavior passes"),
            }
        )
    checks.append(
        {
            "type": "safety",
            "name": "Execution remains disabled",
            "command": "Inspect implementation package execution_policy",
            "expected": "safe_to_execute, safe_to_commit, and safe_to_open_pr are false",
        }
    )
    return checks


def _commit_message(goal: str) -> str:
    return f"Implement {_trim(goal, 72)}"


def _pr_body(goal: str, engineering_spec: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "## Summary",
            "",
            f"Implements: {goal}",
            "",
            "## Engineering Scope",
            "",
            f"Mission type: {engineering_spec.get('mission_type', 'software_factory')}",
            "",
            "## Safety",
            "",
            "- No auth/login/session changes unless explicitly scoped.",
            "- No GitHub Executor execution in this package.",
            "- Requires Founder review before code is applied.",
            "",
            "## Validation",
            "",
            "- Health/readiness check",
            "- Login smoke test",
            "- Board Room smoke test",
            "- New endpoint/package validation",
        ]
    )


def create_implementation_package(*, goal: str, db: Optional[Session] = None, scope: str = "mission_control") -> Dict[str, Any]:
    engineering_spec = create_engineering_spec(goal=goal, db=db, scope=scope)
    proposed_patches = _patch_plan_from_spec(goal, engineering_spec)
    return {
        "mode": "autonomous_senior_software_engineer_v1",
        "scope": scope,
        "goal": goal,
        "engineering_spec": engineering_spec,
        "file_change_plan": [
            {
                "path": patch["path"],
                "change_type": patch["change_type"],
                "patch_type": patch["patch_type"],
                "owner": patch["owner"],
                "purpose": patch["purpose"],
            }
            for patch in proposed_patches
        ],
        "proposed_patches": proposed_patches,
        "tests": engineering_spec.get("test_plan", []),
        "validation_checks": _validation_checks(engineering_spec),
        "commit_message": _commit_message(goal),
        "pr_body": _pr_body(goal, engineering_spec),
        "execution_policy": {
            "safe_to_execute": False,
            "safe_to_commit": False,
            "safe_to_open_pr": False,
            "requires_founder_approval_before_apply": True,
            "requires_human_review": True,
            "reason": "Senior Software Engineer v1 generates implementation packages only. GitHub write execution is intentionally disabled until controlled executor governance is added.",
        },
    }


def format_implementation_package_markdown(package: Dict[str, Any]) -> str:
    lines: List[str] = [
        "## Autonomous Senior Software Engineer v1",
        "",
        f"**Goal:** {package.get('goal', '')}",
        "",
        "### File Change Plan",
    ]
    for item in package.get("file_change_plan", []):
        lines.append(f"- `{item['path']}` — {item['patch_type']}: {item['purpose']}")
    lines.extend(["", "### Proposed Patch Instructions"])
    for patch in package.get("proposed_patches", []):
        lines.append(f"- `{patch['path']}`")
        for instruction in patch.get("instructions", []):
            lines.append(f"  - {instruction}")
    lines.extend(["", "### Validation Checks"])
    for check in package.get("validation_checks", []):
        lines.append(f"- {check['type']}: {check['name']} — {check['expected']}")
    lines.extend(
        [
            "",
            "### Execution Policy",
            f"safe_to_execute: {package.get('execution_policy', {}).get('safe_to_execute')}",
            f"reason: {package.get('execution_policy', {}).get('reason')}",
        ]
    )
    return "\n".join(lines)
