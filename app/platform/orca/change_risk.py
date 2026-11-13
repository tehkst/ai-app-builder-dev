"""The change-risk gate: before the founder lets the team run a plan, show what it will touch.

After planning (engine._plan), `assess` reads the plan's files against the code (the impact map:
what uses each file, which pages and entry points that reaches, which tests cover it), looks for
sensitive areas (payments, sign-in, database structure, deployment, secrets and settings, admin) and,
for client code with a Codebase Map, names the parts and outside services involved. The result is
saved on the mission (`change_risk`) and shown on the approval card in plain words.

A high-risk plan can only be approved with the typed phrase ACK_PHRASE (engine.decide_execution);
the decision records the risk level shown. Declining never needs it. Nothing here is run from the
code and no AI is involved; if the assessment itself fails, the plan is marked "unknown" (treated
like medium) rather than blocking the work.
"""
from __future__ import annotations

import posixpath
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ACK_PHRASE = "APPROVE HIGH RISK"
LEVELS = ("low", "medium", "high", "unknown")
HIGH_DEPENDENTS = 25  # other source files that depend on what changes
MEDIUM_DEPENDENTS = 5
HIGH_ENTRY_POINTS = 10
MANY_FILES = 10
# (area, why it matters, path pattern). Matched on the lower-cased path.
SENSITIVE: Tuple[Tuple[str, str, str], ...] = (
    ("payments", "money can be taken or lost", r"pay|checkout|stripe|paypal|billing|invoice|refund|charge|subscription|gateway"),
    ("sign-in and accounts", "people could be locked out or let in", r"auth|login|logout|signin|sign_in|signup|password|session|oauth|jwt|permission|acl|(^|/)roles?\b"),
    ("database structure", "data can be lost or corrupted", r"migrat|schema|\.sql$|alembic|(^|/)models?(/|\.py$)"),
    ("deployment", "the live site can go down", r"dockerfile|docker-compose|\.github/workflows|deploy|terraform|nginx|\.htaccess|procfile"),
    ("secrets and settings", "keys and settings affect everything", r"(^|/)\.env|wp-config|(^|/)config(/|\.)|settings\.py$"),
    ("admin", "staff tools change what people can do", r"(^|/)(wp-)?admin(/|\.|_)"),
)
HIGH_AREAS = {"payments", "sign-in and accounts", "database structure", "deployment", "secrets and settings"}


def _clean(path: str) -> Optional[str]:
    clean = posixpath.normpath(str(path or "").strip().replace("\\", "/").lstrip("/"))
    return None if not clean or clean.startswith("..") or clean == "." else clean


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _names(paths: List[str], limit: int = 4) -> str:
    shown = ", ".join(paths[:limit])
    return shown + (f" and {len(paths) - limit} more" if len(paths) > limit else "")


def assess(workspace: str, tasks: List[Any], map_context: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """The risk of running these planned tasks on the code in `workspace`. `map_context` (from the
    codebase's map, when there is one) gives each file's part and the outside services it talks to."""
    from app.platform.impact_map import build_map, impact

    root = Path(workspace)
    planned: List[str] = []
    unnamed = 0
    for task in tasks:
        if getattr(task, "status", "pending") == "passed":
            continue  # already done in an earlier round
        files = [p for p in (_clean(f) for f in getattr(task, "files", []) or []) if p]
        unnamed += 0 if files else 1
        planned += [p for p in files if p not in planned]
    existing = [p for p in planned if (root / p).is_file()]
    new = [p for p in planned if p not in existing]

    imap = build_map(str(root))
    dependents, entry_points, untested = set(), set(), []
    for path in existing:
        reach = impact(imap, path)
        if not reach.get("found"):
            continue
        dependents |= {a["path"] for a in reach["affected"] if not imap.is_test(a["path"])}
        entry_points |= set(reach["entry_points"])
        if reach["untested"] and not imap.is_test(path):
            untested.append(path)
    dependents -= set(existing)

    areas: Dict[str, List[str]] = {}
    for path in planned:
        for area, _, pattern in SENSITIVE:
            if re.search(pattern, path.lower()):
                areas.setdefault(area, []).append(path)
    parts, services = [], []
    for path in planned:
        info = (map_context or {}).get(path) or {}
        if info.get("part") and info["part"] not in parts:
            parts.append(info["part"])
        services += [s for s in info.get("services") or [] if s not in services]
        if {s.lower() for s in info.get("services") or []} & {"stripe", "paypal", "square", "braintree"}:
            areas.setdefault("payments", [])
            areas["payments"] += [path] if path not in areas["payments"] else []

    reasons: List[str] = []
    why = {area: reason for area, reason, _ in SENSITIVE}
    for area, paths in areas.items():
        reasons.append(f"Touches {area} ({why[area]}): {_names(paths)}.")
    if dependents:
        reasons.append(f"{_plural(len(dependents), 'other file')} depend on the files it changes"
                       + (f"; {_plural(len(entry_points), 'page or entry point')} could be affected." if entry_points else "."))
    elif existing:
        reasons.append("Nothing else in the code depends on the files it changes.")
    if untested:
        reasons.append(f"No tests cover {_names(untested)}, so a mistake there may go unnoticed.")
    if new:
        reasons.append(f"Adds {_plural(len(new), 'new file')}: {_names(new)}.")
    if unnamed:
        reasons.append(f"The plan doesn't say which files {_plural(unnamed, 'task')} will change, so the "
                       "real reach may be wider than shown.")
    if services:
        reasons.append(f"Code that talks to {', '.join(services[:5])} is involved.")

    if set(areas) & HIGH_AREAS or len(dependents) >= HIGH_DEPENDENTS or len(entry_points) >= HIGH_ENTRY_POINTS:
        level = "high"
    elif (areas or len(dependents) >= MEDIUM_DEPENDENTS or (untested and dependents) or unnamed
          or len(planned) > MANY_FILES or services):
        level = "medium"
    else:
        level = "low"
    if not reasons:
        reasons.append("The plan names no files, so its reach can't be shown; review the plan yourself.")
    headline = {"low": "Low risk: a small, contained change.",
                "medium": "Medium risk: check the reasons before approving.",
                "high": f"High risk: approving needs the typed phrase {ACK_PHRASE}."}[level]
    return {"level": level, "headline": headline, "reasons": reasons[:8],
            "files": {"changed": existing[:50], "new": new[:50], "unnamed_tasks": unnamed},
            "dependents": len(dependents), "entry_points": sorted(entry_points)[:20], "untested": untested[:20],
            "areas": sorted(areas), "parts": parts[:10], "services": services[:10]}


def assess_safely(workspace: str, tasks: List[Any], map_context: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """`assess`, but a failure gives an "unknown" risk instead of stopping the mission."""
    try:
        return assess(workspace, tasks, map_context)
    except Exception as exc:  # the gate must never block work by crashing
        return {"level": "unknown", "headline": "Risk unknown: the check couldn't read the code.",
                "reasons": [f"The risk check failed ({type(exc).__name__}); review the plan yourself before approving."],
                "files": {"changed": [], "new": [], "unnamed_tasks": 0}, "dependents": 0, "entry_points": [],
                "untested": [], "areas": [], "parts": [], "services": []}


def needs_ack(risk: Optional[Dict[str, Any]]) -> bool:
    return bool(risk) and risk.get("level") == "high"
