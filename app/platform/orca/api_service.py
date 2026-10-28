"""Mission Control API for Orca missions (founder-only, registered in app/platform/server.py).

Every call is a POST carrying the founder's session token (same pattern as other governed
Mission Control actions). Long work (planning, Builder <-> QA) runs in the background via
runner.py; the page polls `orca/mission` for progress. Workspaces are chosen by *name* under the
approved sandbox base; no caller ever supplies a filesystem path.
"""
from __future__ import annotations

import re
import threading
from typing import Any, Callable, Dict, List, Optional

from app.platform.auth.service import require_founder
from app.platform.orca import runner
from app.platform.orca.engine import Orca
from app.platform.orca.models import Mission
from app.platform.services.materialization_sandbox_writer_service import APPROVED_SANDBOX_ROOT_BASE

CONTRACT = "orca-missions-v1"
WORKSPACE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
BOARD_ROOM_MISSION_ID = re.compile(r"^MISSION-[A-F0-9]{12}$")
MAX_GOAL_CHARS = 4_000

# Replaceable for checks (scripted employees); production builds a real Orca per run.
_orca_factory: Callable[[], Orca] = Orca
_START_LOCK = threading.Lock()  # check-then-start on a workspace is atomic (double clicks, two tabs)


def _ok(**fields: Any) -> Dict[str, Any]:
    return {"contract": CONTRACT, "status": "ok", **fields}


def _error(message: str) -> Dict[str, Any]:
    return {"contract": CONTRACT, "status": "error", "error": message}


def _founder(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    founder = require_founder(payload or {})
    return founder if founder.get("authorized") else None


def _unauthorized() -> Dict[str, Any]:
    return {"contract": CONTRACT, "status": "unauthorized", "authenticated": False}


def _board_room_origin(source: Any) -> Optional[str]:
    """The Board Room proposal a mission came from (a traceability label only; it grants nothing)."""
    value = str((source or {}).get("board_room_mission_id") or "") if isinstance(source, dict) else ""
    return value if BOARD_ROOM_MISSION_ID.match(value) else None


def _summary(mission: Mission) -> Dict[str, Any]:
    return {
        "mission_id": mission.mission_id, "goal": mission.goal, "status": mission.status,
        "running": runner.is_running(mission.mission_id),
        "execution_approval": mission.execution_approval,
        "workspace": mission.workspace_root.rsplit("/", 1)[-1],
        "tasks_total": len(mission.tasks), "tasks_passed": sum(t.status == "passed" for t in mission.tasks),
        "paused_reason": mission.paused_reason, "escalation": (mission.escalation or {}).get("reason"),
        "created_at": mission.created_at, "updated_at": mission.updated_at,
        "origin": "board_room" if any(e.get("event") == "started_from_board_room" for e in mission.events) else "mission_control",
        "client": (mission.client or {}).get("client_name"), "sandboxed": mission.sandboxed,
        "cost": _cost(mission), "questions": mission.questions,
        "now": _now_line(mission) if runner.is_running(mission.mission_id) else None,
    }


def _activity(mission: Mission, limit: int = 12) -> List[Dict[str, Any]]:
    store = _orca_factory().store
    try:
        return store.activity(mission.mission_id)[-limit:]
    except Exception:  # the live feed is a convenience; never break the mission view
        return []


def _now_line(mission: Mission) -> Optional[str]:
    lines = _activity(mission, 1)
    return f"{lines[-1]['employee']}: {lines[-1]['detail']}" if lines else None


def _cost(mission: Mission) -> Dict[str, Any]:
    from app.platform.ai_costs import summarize

    return summarize(mission.usage)


def _launch(mission: Mission) -> bool:
    """Run the mission in the background unless another mission is running on its workspace."""
    busy = runner.workspace_busy(mission.workspace_root, mission.mission_id)
    if busy:
        raise ValueError(f"Mission {busy} is already working on this workspace; wait for it to stop.")
    return runner.start_background_run(mission.mission_id, _orca_factory, mission.workspace_root)


def _check_workspace_free(mission: Mission) -> None:
    busy = runner.workspace_busy(mission.workspace_root, mission.mission_id)
    if busy:
        raise ValueError(f"Mission {busy} is already working on this workspace; wait for it to stop.")


def _load(orca: Orca, payload: Dict[str, Any]) -> Mission:
    mission_id = str(payload.get("mission_id") or "").strip()
    mission = orca.store.load(mission_id) if mission_id else None
    if mission is None:
        raise ValueError("Mission not found.")
    return mission


def _guarded(handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]):
    def call(payload: Dict[str, Any]) -> Dict[str, Any]:
        founder = _founder(payload)
        if founder is None:
            return _unauthorized()
        try:
            return handler(payload or {}, founder)
        except ValueError as exc:
            return _error(str(exc))
    call.__name__ = handler.__name__
    return call


@_guarded
def list_orca_missions(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    orca = _orca_factory()
    missions = [m for m in (orca.store.load(i) for i in orca.store.list_ids()) if m is not None]
    missions.sort(key=lambda m: m.updated_at, reverse=True)
    return _ok(missions=[_summary(m) for m in missions])


@_guarded
def get_orca_mission(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    mission = _load(_orca_factory(), payload)
    return _ok(mission={**mission.to_dict(), "running": runner.is_running(mission.mission_id), "cost": _cost(mission),
                        "activity": _activity(mission)})


@_guarded
def list_orca_workspaces(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    base = APPROVED_SANDBOX_ROOT_BASE
    names = sorted(p.name for p in base.iterdir() if p.is_dir() and WORKSPACE_NAME.match(p.name)) if base.is_dir() else []
    return _ok(workspaces=names, base=str(base))


@_guarded
def start_orca_mission(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    goal = str(payload.get("goal") or "").strip()
    name = str(payload.get("workspace") or "").strip()
    if not goal or len(goal) > MAX_GOAL_CHARS:
        raise ValueError(f"Describe the goal (1-{MAX_GOAL_CHARS} characters).")
    if not WORKSPACE_NAME.match(name):
        raise ValueError("Choose a workspace from the list.")
    orca = _orca_factory()
    workspace = str((APPROVED_SANDBOX_ROOT_BASE / name).resolve())
    with _START_LOCK:
        busy = runner.workspace_busy(workspace)
        if busy:
            raise ValueError(f"Mission {busy} is already working on '{name}'; wait for it to stop.")
        mission = orca.start_mission(goal, workspace, execution_approved=payload.get("execution_approved") is True)
        mission.record("started_from_mission_control", by=founder.get("email") or "founder")
        origin = _board_room_origin(payload.get("source"))
        if origin:
            mission.record("started_from_board_room", board_room_mission_id=origin)
        orca.store.save(mission)
        _launch(mission)
    return _ok(mission=_summary(mission))


@_guarded
def decide_orca_execution(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload.get("approved"), bool):
        raise ValueError("'approved' must be true or false.")
    orca = _orca_factory()
    current = _load(orca, payload)
    _check_workspace_free(current)
    mission = orca.decide_execution(current.mission_id, approved=payload["approved"],
                                    decided_by=founder.get("email") or "founder")
    _launch(mission)
    return _ok(mission=_summary(mission))


@_guarded
def run_orca_mission(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    orca = _orca_factory()
    mission = _load(orca, payload)
    if mission.finished:
        raise ValueError(f"Mission is already {mission.status}.")
    if mission.status == "awaiting_execution_approval":
        raise ValueError("Mission is waiting for your execution decision.")
    if runner.is_running(mission.mission_id):
        return _ok(mission=_summary(mission), started=False)
    started = _launch(mission)
    return _ok(mission=_summary(mission), started=started)


@_guarded
def answer_orca_questions(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload.get("answers"), list):
        raise ValueError("'answers' must be a list, one per question.")
    orca = _orca_factory()
    current = _load(orca, payload)
    _check_workspace_free(current)
    mission = orca.answer_questions(current.mission_id, payload["answers"], decided_by=founder.get("email") or "founder")
    _launch(mission)
    return _ok(mission=_summary(mission))


@_guarded
def retry_orca_task(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    orca = _orca_factory()
    current = _load(orca, payload)
    _check_workspace_free(current)
    checks = payload.get("acceptance_checks")
    if checks is not None and not (isinstance(checks, list) and all(isinstance(c, str) for c in checks)):
        raise ValueError("'acceptance_checks' must be a list of commands.")
    mission = orca.retry_task(current.mission_id, decided_by=founder.get("email") or "founder",
                              acceptance_checks=checks)
    _launch(mission)
    return _ok(mission=_summary(mission))


@_guarded
def list_orca_workforce(payload: Dict[str, Any], founder: Dict[str, Any]) -> Dict[str, Any]:
    """The AI team as the founder sees it: who they are and what each one does."""
    from app.platform.orca.workforce import load_planned_hires

    team = _orca_factory().workforce.employees.values()
    return _ok(team=[{"id": e.employee_id, "name": e.name, "department": e.department, "summary": e.summary,
                      "role": _team_role(e.responsibilities)} for e in team], planned=load_planned_hires())


def _team_role(responsibilities) -> str:
    if any(r.startswith("build_task") for r in responsibilities):
        return "builder"
    if any(r.startswith("review") for r in responsibilities):
        return "reviewer"
    if any(r.startswith("audit") for r in responsibilities):
        return "auditor"
    return "planner" if "plan_mission" in responsibilities else "specialist"
