from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.executive_context_service import format_context_block
from app.platform.services.software_factory_planner import create_software_factory_plan


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "sprint"


def _priority(title: str, index: int) -> str:
    lowered = title.lower()
    if any(word in lowered for word in ("auth", "login", "production", "rollback", "security")):
        return "P0"
    if index <= 2:
        return "P1"
    if index <= 4:
        return "P2"
    return "P3"


def _risk_score(title: str, description: str) -> int:
    text = f"{title} {description}".lower()
    score = 2
    if any(word in text for word in ("auth", "login", "session", "database", "migration", "deploy")):
        score += 4
    if any(word in text for word in ("executor", "write", "commit", "repository", "pr")):
        score += 3
    if any(word in text for word in ("ui", "polish", "copy", "display")):
        score -= 1
    return max(1, min(score, 10))


def _lane(owner: str, title: str) -> str:
    text = f"{owner} {title}".lower()
    if any(word in text for word in ("backend", "api", "service", "database")):
        return "backend"
    if any(word in text for word in ("product", "ui", "ux", "frontend")):
        return "frontend"
    if any(word in text for word in ("qa", "validation", "test")):
        return "qa"
    if any(word in text for word in ("counsel", "approval", "security", "risk")):
        return "governance"
    return "platform"


def _story_from_task(task: Dict[str, Any], index: int, epic_title: str) -> Dict[str, Any]:
    title = task.get("title", f"Story {index}")
    description = task.get("description", "Complete planned work item.")
    return {
        "id": f"story-{index}-{_slug(title)}",
        "title": title,
        "epic": epic_title,
        "description": description,
        "owner": task.get("owner", "Mission Control"),
        "lane": _lane(task.get("owner", ""), title),
        "priority": _priority(title, index),
        "risk_score": _risk_score(title, description),
        "dependencies": task.get("depends_on", []),
        "status": "backlog",
        "acceptance_criteria": [
            "Implementation is reviewable as a small change.",
            "Existing login, Board Room, and health checks are not regressed.",
            "Rollback notes are clear before merge.",
        ],
    }


def _extract_stories(factory_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    stories: List[Dict[str, Any]] = []
    index = 1
    for epic in factory_plan.get("plan", {}).get("epics", []):
        epic_title = epic.get("title", "Epic")
        for feature in epic.get("features", []):
            for task in feature.get("tasks", []):
                stories.append(_story_from_task(task, index, epic_title))
                index += 1
    return stories


def _dependency_order(stories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(stories, key=lambda item: (item.get("priority", "P9"), item.get("risk_score", 10), item.get("id", "")))


def _sprint_window(days: int) -> Dict[str, str]:
    start = _now()
    end = start + timedelta(days=days)
    return {"start": start.date().isoformat(), "end": end.date().isoformat(), "duration_days": str(days)}


def create_autonomous_sprint(
    *,
    goal: str,
    sprint_days: int = 7,
    capacity_points: int = 20,
    db: Optional[Session] = None,
    scope: str = "mission_control",
) -> Dict[str, Any]:
    context_block = format_context_block(db=db, scope=scope) if db is not None else "No persistent executive context has been captured yet."
    factory_plan = create_software_factory_plan(goal=goal, db=db, scope=scope)
    stories = _dependency_order(_extract_stories(factory_plan))
    committed: List[Dict[str, Any]] = []
    total_points = 0
    for story in stories:
        points = 5 if story["risk_score"] >= 7 else 3 if story["risk_score"] >= 4 else 2
        if total_points + points <= capacity_points:
            story = dict(story)
            story["estimate_points"] = points
            story["status"] = "committed"
            committed.append(story)
            total_points += points
    return {
        "mode": "autonomous_sprint_engine_v1",
        "scope": scope,
        "goal": goal,
        "sprint": {
            "id": f"sprint-{_slug(goal)}",
            "window": _sprint_window(sprint_days),
            "capacity_points": capacity_points,
            "committed_points": total_points,
            "status": "planned_pending_founder_review",
        },
        "context_available": "No persistent" not in context_block,
        "factory_plan": factory_plan,
        "backlog": stories,
        "committed_stories": committed,
        "execution_lanes": {
            "backend": [story for story in committed if story["lane"] == "backend"],
            "frontend": [story for story in committed if story["lane"] == "frontend"],
            "platform": [story for story in committed if story["lane"] == "platform"],
            "qa": [story for story in committed if story["lane"] == "qa"],
            "governance": [story for story in committed if story["lane"] == "governance"],
        },
        "review_cadence": [
            {"day": 1, "focus": "Confirm scope and protected boundaries."},
            {"day": max(2, sprint_days // 2), "focus": "Review risk, blockers, and dependency drift."},
            {"day": sprint_days, "focus": "Sprint review, validation, deploy readiness, and next backlog refresh."},
        ],
        "sprint_policy": {
            "autonomous_execution_enabled": False,
            "requires_founder_review": True,
            "requires_repository_gateway": True,
            "reason": "Sprint Engine v1 plans and prioritizes work only. Repository execution remains governed by the approval gateway.",
        },
    }


def format_sprint_markdown(sprint_plan: Dict[str, Any]) -> str:
    sprint = sprint_plan.get("sprint", {})
    lines = [
        "## Autonomous Sprint Engine",
        "",
        f"**Goal:** {sprint_plan.get('goal', '')}",
        f"**Sprint:** {sprint.get('id', '')}",
        f"**Status:** {sprint.get('status', '')}",
        f"**Capacity:** {sprint.get('committed_points', 0)}/{sprint.get('capacity_points', 0)} points",
        "",
        "### Committed Stories",
    ]
    for story in sprint_plan.get("committed_stories", []):
        lines.append(f"- {story['priority']} `{story['id']}` — {story['title']} ({story['lane']}, risk {story['risk_score']})")
    lines.extend(["", "### Review Cadence"])
    for item in sprint_plan.get("review_cadence", []):
        lines.append(f"- Day {item['day']}: {item['focus']}")
    lines.extend(["", "### Policy"])
    for key, value in sprint_plan.get("sprint_policy", {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
