from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.board_room_orchestrator import run_executive_orchestration
from app.platform.services.executive_context_service import format_context_block


def _trim(text: str, limit: int = 900) -> str:
    return (text or "").strip()[:limit]


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:48] or "mission"


def _mission_type(goal: str) -> str:
    lowered = goal.lower()
    if any(word in lowered for word in ("ui", "ux", "workspace", "composer", "sidebar")):
        return "product_ui"
    if any(word in lowered for word in ("api", "backend", "database", "memory", "orchestrator", "planner")):
        return "backend_platform"
    if any(word in lowered for word in ("deploy", "cloud run", "ci", "github actions")):
        return "platform_ops"
    if any(word in lowered for word in ("agent", "multi-agent", "board room", "executive")):
        return "ai_system"
    return "software_factory"


def _risk_controls(mission_type: str) -> list[str]:
    base = [
        "Keep auth, login, session handling, and deployment configuration unchanged unless explicitly scoped.",
        "Prefer small additive changes over broad refactors.",
        "Preserve existing endpoints and UI behavior unless the acceptance criteria require a change.",
        "Every implementation PR must include rollback notes and manual validation steps.",
    ]
    if mission_type in {"backend_platform", "ai_system"}:
        base.append("Expose new behavior behind additive endpoints or isolated service functions before replacing current flows.")
    if mission_type == "product_ui":
        base.append("Validate the Board Room visually after deploy with a hard refresh and a real founder prompt.")
    return base


def _acceptance_criteria(goal: str, mission_type: str) -> list[str]:
    criteria = [
        "The mission has a clear Founder-facing outcome.",
        "The implementation can be reviewed as one or more small PRs.",
        "Existing Mission Control login and Board Room chat continue to work.",
    ]
    if mission_type == "backend_platform":
        criteria.extend([
            "New backend behavior is available through a stable service or endpoint.",
            "Existing routes remain backward-compatible.",
        ])
    elif mission_type == "ai_system":
        criteria.extend([
            "The AI behavior returns structured output that can drive future automation.",
            "The response includes confidence, risks, and next action.",
        ])
    elif mission_type == "product_ui":
        criteria.extend([
            "The UI remains readable at laptop width.",
            "No overlays or action cards overlap conversation content.",
        ])
    else:
        criteria.append(f"The delivered work directly advances: {goal[:160]}.")
    return criteria


def _task(title: str, owner: str, description: str, depends_on: Optional[list[str]] = None) -> dict[str, Any]:
    return {
        "id": _slug(title),
        "title": title,
        "owner": owner,
        "description": description,
        "depends_on": depends_on or [],
        "status": "planned",
    }


def _build_plan(goal: str, mission_type: str, orchestration: dict[str, Any]) -> dict[str, Any]:
    mission_slug = _slug(goal)
    epics = [
        {
            "id": f"{mission_slug}-foundation",
            "title": "Foundation and scope guard",
            "objective": "Define the smallest safe implementation boundary and protect existing production-critical flows.",
            "features": [
                {
                    "id": f"{mission_slug}-contract",
                    "title": "Mission contract",
                    "tasks": [
                        _task("Define acceptance criteria", "Engineering Director", "Convert the founder goal into testable acceptance criteria."),
                        _task("Confirm protected boundaries", "General Counsel", "List auth, deployment, and executor boundaries that must not change."),
                    ],
                }
            ],
        },
        {
            "id": f"{mission_slug}-implementation",
            "title": "Implementation path",
            "objective": "Deliver the requested capability through small reviewable changes.",
            "features": [
                {
                    "id": f"{mission_slug}-service",
                    "title": "Core capability service",
                    "tasks": [
                        _task("Add isolated service", "Backend Engineer", "Implement the capability in an isolated service module.", [f"{mission_slug}-contract"]),
                        _task("Expose additive API", "Backend Engineer", "Expose a small endpoint or integration seam without replacing existing flows.", ["add-isolated-service"]),
                    ],
                },
                {
                    "id": f"{mission_slug}-integration",
                    "title": "Founder workflow integration",
                    "tasks": [
                        _task("Bind to Board Room", "Product Engineer", "Surface the capability in Mission Control only after the backend contract is stable.", ["expose-additive-api"]),
                        _task("Add validation path", "QA Lead", "Document manual validation and rollback checks.", ["bind-to-board-room"]),
                    ],
                },
            ],
        },
    ]
    if mission_type in {"ai_system", "software_factory"}:
        epics.append(
            {
                "id": f"{mission_slug}-automation-readiness",
                "title": "Automation readiness",
                "objective": "Prepare the result to be consumed by future autonomous coding teams.",
                "features": [
                    {
                        "id": f"{mission_slug}-structured-output",
                        "title": "Structured output contract",
                        "tasks": [
                            _task("Return machine-readable plan", "AI Systems Engineer", "Ensure output includes epics, features, tasks, dependencies, risks, and recommended PR sequence."),
                            _task("Add confidence and risk fields", "AI Systems Engineer", "Include confidence and risk metadata for future execution agents."),
                        ],
                    }
                ],
            }
        )
    return {"epics": epics}


def _pr_sequence(goal: str, mission_type: str) -> list[dict[str, Any]]:
    slug = _slug(goal)
    sequence = [
        {
            "pr": 1,
            "branch_hint": f"{slug}-foundation",
            "title": "Foundation service and contracts",
            "scope": "Add isolated service, structured models, and validation contract.",
            "merge_gate": "Existing login, health, and Board Room smoke tests pass.",
        },
        {
            "pr": 2,
            "branch_hint": f"{slug}-integration",
            "title": "Mission Control integration",
            "scope": "Bind the service to the relevant Board Room or Mission Control flow.",
            "merge_gate": "Founder-facing behavior works without regressions.",
        },
    ]
    if mission_type in {"product_ui", "ai_system"}:
        sequence.append(
            {
                "pr": 3,
                "branch_hint": f"{slug}-polish-validation",
                "title": "Polish and validation",
                "scope": "Tighten UX, response shape, telemetry notes, and rollback guidance.",
                "merge_gate": "Manual production validation checklist is complete.",
            }
        )
    return sequence


def create_software_factory_plan(*, goal: str, db: Optional[Session] = None, scope: str = "mission_control") -> Dict[str, Any]:
    mission_type = _mission_type(goal)
    context_block = format_context_block(db=db, scope=scope) if db is not None else "No persistent executive context has been captured yet."
    orchestration = run_executive_orchestration(message=goal, db=db, scope=scope)
    plan = _build_plan(goal, mission_type, orchestration)
    risks = _risk_controls(mission_type)
    acceptance = _acceptance_criteria(goal, mission_type)
    sequence = _pr_sequence(goal, mission_type)
    return {
        "mode": "autonomous_software_factory_planner",
        "scope": scope,
        "goal": goal,
        "mission_type": mission_type,
        "context_available": "No persistent" not in context_block,
        "context_excerpt": _trim(context_block, 800),
        "orchestration": orchestration,
        "plan": plan,
        "acceptance_criteria": acceptance,
        "risk_controls": risks,
        "recommended_pr_sequence": sequence,
        "execution_policy": {
            "requires_founder_approval_before_code": True,
            "requires_review_before_merge": True,
            "safe_to_autocode": False,
            "reason": "Planner produces implementation structure only. Code execution remains founder-approved until autonomous coding controls are implemented.",
        },
    }


def format_factory_plan_markdown(factory_plan: Dict[str, Any]) -> str:
    lines: List[str] = [
        "## Autonomous Software Factory Plan",
        "",
        f"**Goal:** {factory_plan.get('goal', '')}",
        f"**Mission type:** {factory_plan.get('mission_type', '').replace('_', ' ')}",
        f"**Context:** {'available' if factory_plan.get('context_available') else 'not yet available'}",
        "",
        "### Acceptance Criteria",
    ]
    for item in factory_plan.get("acceptance_criteria", []):
        lines.append(f"- {item}")
    lines.extend(["", "### Epics / Features / Tasks"])
    for epic in factory_plan.get("plan", {}).get("epics", []):
        lines.append(f"- **{epic['title']}** — {epic['objective']}")
        for feature in epic.get("features", []):
            lines.append(f"  - {feature['title']}")
            for task in feature.get("tasks", []):
                lines.append(f"    - {task['title']} ({task['owner']})")
    lines.extend(["", "### Recommended PR Sequence"])
    for pr in factory_plan.get("recommended_pr_sequence", []):
        lines.append(f"- **PR {pr['pr']}: {pr['title']}** — {pr['scope']}")
    lines.extend(["", "### Risk Controls"])
    for item in factory_plan.get("risk_controls", []):
        lines.append(f"- {item}")
    return "\n".join(lines)
