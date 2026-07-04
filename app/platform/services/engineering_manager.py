from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.software_factory_planner import create_software_factory_plan


def _trim(text: str, limit: int = 900) -> str:
    return (text or "").strip()[:limit]


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "mission"


def _architecture_for_type(mission_type: str) -> Dict[str, Any]:
    if mission_type == "product_ui":
        return {
            "style": "thin UI integration over existing backend contracts",
            "layers": ["Mission Control UI renderer", "Board Room client-side integration", "existing backend endpoints"],
            "principles": ["preserve login", "avoid modal overlays", "ship visual changes separately from behavior changes"],
        }
    if mission_type == "backend_platform":
        return {
            "style": "additive service plus API router",
            "layers": ["service module", "FastAPI route", "optional persistence model", "manual validation"],
            "principles": ["new endpoint before replacement", "stable response contract", "no deployment config change"],
        }
    if mission_type == "ai_system":
        return {
            "style": "structured AI capability service",
            "layers": ["orchestration service", "structured output contract", "Board Room binding", "memory/context integration"],
            "principles": ["machine-readable output", "confidence and risks", "human approval gate"],
        }
    return {
        "style": "small additive platform capability",
        "layers": ["service", "API", "integration seam", "validation"],
        "principles": ["small PRs", "reversible changes", "clear acceptance criteria"],
    }


def _file_change_map(goal: str, mission_type: str) -> List[Dict[str, Any]]:
    slug = _slug(goal)
    files: List[Dict[str, Any]] = [
        {
            "path": f"app/platform/services/{slug}.py",
            "change_type": "add",
            "owner": "Backend Engineer",
            "purpose": "Implement the isolated core service for the mission.",
        },
        {
            "path": f"app/platform/api/{slug}_api.py",
            "change_type": "add",
            "owner": "Backend Engineer",
            "purpose": "Expose the service through an additive API endpoint.",
        },
        {
            "path": "app/main.py",
            "change_type": "modify",
            "owner": "Platform Engineer",
            "purpose": "Register the new router without changing existing routes.",
        },
    ]
    if mission_type == "product_ui":
        files.append(
            {
                "path": "app/platform/ui/founder_dashboard_board_chat.py",
                "change_type": "modify",
                "owner": "Product Engineer",
                "purpose": "Bind the capability into the Board Room workspace.",
            }
        )
    if mission_type in {"backend_platform", "ai_system"}:
        files.append(
            {
                "path": "app/platform/services/*_validation.py",
                "change_type": "optional_add",
                "owner": "QA Lead",
                "purpose": "Add deterministic validation helpers if the mission requires structured verification.",
            }
        )
    return files


def _contracts(goal: str, mission_type: str) -> Dict[str, Any]:
    slug = _slug(goal)
    return {
        "api_contract": {
            "method": "POST",
            "path": f"/platform/{slug}/execute",
            "request": {"token": "optional string", "goal": "string", "scope": "mission_control"},
            "response": {
                "mode": slug.replace("-", "_"),
                "result": "structured object",
                "markdown": "human-readable summary",
                "execution_policy": "approval and safety metadata",
            },
        },
        "data_contract": {
            "persistence_required": mission_type in {"backend_platform", "ai_system"},
            "tables": [] if mission_type == "product_ui" else [f"platform_{slug.replace('-', '_')}_events optional"],
            "migration_policy": "Use additive table creation only; avoid destructive schema changes.",
        },
        "ui_contract": {
            "surface": "Board Room Executive Workspace" if mission_type in {"product_ui", "ai_system"} else "API first, UI later",
            "founder_visible_behavior": "Show structured recommendation, next action, and validation status.",
        },
    }


def _implementation_order(factory_plan: Dict[str, Any], mission_type: str) -> List[Dict[str, Any]]:
    order = [
        {"step": 1, "name": "Confirm scope guard", "owner": "Engineering Manager", "exit_criteria": "Protected boundaries are explicit."},
        {"step": 2, "name": "Implement isolated service", "owner": "Backend Engineer", "exit_criteria": "Service returns deterministic structured output."},
        {"step": 3, "name": "Expose additive endpoint", "owner": "Backend Engineer", "exit_criteria": "Endpoint returns service output without replacing existing flows."},
        {"step": 4, "name": "Register router", "owner": "Platform Engineer", "exit_criteria": "Application starts and health checks remain green."},
    ]
    if mission_type in {"product_ui", "ai_system"}:
        order.append({"step": 5, "name": "Bind UI seam", "owner": "Product Engineer", "exit_criteria": "Founder can access the capability from Mission Control."})
    order.append({"step": len(order) + 1, "name": "Validate and document rollback", "owner": "QA Lead", "exit_criteria": "Manual checks and rollback command are documented."})
    return order


def _test_plan(mission_type: str) -> List[Dict[str, str]]:
    tests = [
        {"type": "smoke", "name": "Health readiness", "command": "GET /health/readiness", "expected": "healthy response"},
        {"type": "manual", "name": "Login check", "command": "Open Mission Control and login", "expected": "login still works"},
        {"type": "manual", "name": "Board Room check", "command": "Send a Board Room prompt", "expected": "response renders normally"},
    ]
    if mission_type != "product_ui":
        tests.append({"type": "api", "name": "New endpoint check", "command": "POST new endpoint with sample payload", "expected": "structured response"})
    else:
        tests.append({"type": "ui", "name": "Workspace layout check", "command": "Hard refresh Mission Control", "expected": "no overlap or layout regression"})
    return tests


def _team_handoff(goal: str, mission_type: str) -> List[Dict[str, str]]:
    return [
        {"team": "Backend Engineer", "brief": "Own service logic, endpoint contract, response shape, and safe defaults."},
        {"team": "Product Engineer", "brief": "Own Founder-facing Board Room integration if UI exposure is in scope."},
        {"team": "QA Lead", "brief": "Own smoke checks, manual validation, and rollback checklist."},
        {"team": "Reviewer", "brief": "Block broad refactors, auth/session changes, and deployment config drift."},
    ]


def create_engineering_spec(*, goal: str, db: Optional[Session] = None, scope: str = "mission_control") -> Dict[str, Any]:
    factory_plan = create_software_factory_plan(goal=goal, db=db, scope=scope)
    mission_type = factory_plan.get("mission_type", "software_factory")
    return {
        "mode": "autonomous_engineering_manager",
        "scope": scope,
        "goal": goal,
        "mission_type": mission_type,
        "factory_plan": factory_plan,
        "architecture": _architecture_for_type(mission_type),
        "file_change_map": _file_change_map(goal, mission_type),
        "contracts": _contracts(goal, mission_type),
        "implementation_order": _implementation_order(factory_plan, mission_type),
        "test_plan": _test_plan(mission_type),
        "risk_controls": factory_plan.get("risk_controls", []),
        "rollback_plan": [
            "Do not merge if login, health, or Board Room smoke checks fail.",
            "If production regresses after deploy, shift Cloud Run traffic back to the previous known-good revision.",
            "If API shape is wrong, revert the additive PR rather than modifying protected flows under pressure.",
        ],
        "coding_team_handoff": _team_handoff(goal, mission_type),
        "execution_policy": {
            "safe_to_autocode": False,
            "requires_founder_approval_before_code": True,
            "requires_human_merge": True,
            "reason": "Engineering Manager creates the implementation specification only. Autonomous coding starts in the next controlled milestone.",
        },
    }


def format_engineering_spec_markdown(spec: Dict[str, Any]) -> str:
    lines: List[str] = [
        "## Autonomous Engineering Manager Spec",
        "",
        f"**Goal:** {spec.get('goal', '')}",
        f"**Mission type:** {spec.get('mission_type', '').replace('_', ' ')}",
        "",
        "### Architecture",
        f"- Style: {spec.get('architecture', {}).get('style', '')}",
    ]
    for layer in spec.get("architecture", {}).get("layers", []):
        lines.append(f"- Layer: {layer}")
    lines.extend(["", "### File Change Map"])
    for item in spec.get("file_change_map", []):
        lines.append(f"- `{item['path']}` — {item['change_type']} — {item['owner']}: {item['purpose']}")
    lines.extend(["", "### Implementation Order"])
    for item in spec.get("implementation_order", []):
        lines.append(f"- {item['step']}. {item['name']} ({item['owner']}) — {item['exit_criteria']}")
    lines.extend(["", "### Test Plan"])
    for item in spec.get("test_plan", []):
        lines.append(f"- {item['type']}: {item['name']} — {item['expected']}")
    lines.extend(["", "### Rollback"])
    for item in spec.get("rollback_plan", []):
        lines.append(f"- {item}")
    return "\n".join(lines)
