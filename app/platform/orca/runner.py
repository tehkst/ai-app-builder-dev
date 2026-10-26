"""Run Orca missions in the background so HTTP requests return immediately.

One thread per mission at most; a second request for a mission that is already running is a
no-op. Runs are in-process: if the server restarts mid-mission, the saved state is intact; the
always-on service (ORCA_AUTO_RESUME=1) picks interrupted missions back up at startup, otherwise
the founder resumes them with "Run". An unexpected crash pauses the mission with the error, so it
never silently stalls.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from app.platform.orca.engine import Orca

OrcaFactory = Callable[[], Orca]

_RUNNING: Dict[str, threading.Thread] = {}
_WORKSPACES: Dict[str, str] = {}  # mission_id -> resolved workspace of its current run
_LOCK = threading.Lock()


def _busy_locked(workspace: str, except_mission: str = "") -> Optional[str]:
    for mission_id, thread in _RUNNING.items():
        if mission_id != except_mission and thread.is_alive() and _WORKSPACES.get(mission_id) == workspace:
            return mission_id
    return None


def workspace_busy(workspace: str, except_mission: str = "") -> Optional[str]:
    """The mission currently running on this workspace, if any (two Builder/QA loops must never
    edit the same files at once)."""
    with _LOCK:
        return _busy_locked(workspace, except_mission)


def is_running(mission_id: str) -> bool:
    with _LOCK:
        thread = _RUNNING.get(mission_id)
        return bool(thread and thread.is_alive())


def running_ids() -> List[str]:
    with _LOCK:
        return sorted(mid for mid, thread in _RUNNING.items() if thread.is_alive())


def _record_crash(orca: Orca, mission_id: str, error: Exception) -> None:
    mission = orca.store.load(mission_id)
    if mission is None or mission.finished:
        return
    if mission.status != "paused":
        mission.resume_status, mission.status = mission.status, "paused"
    mission.paused_reason = f"Orca stopped unexpectedly: {type(error).__name__}: {error}"
    mission.record("runner_crashed", error=str(error)[:500])
    orca.store.save(mission)


def start_background_run(mission_id: str, factory: OrcaFactory, workspace: str = "") -> bool:
    """Start running the mission in a thread. Returns False if it is already running, or if another
    mission is running on the same workspace."""
    with _LOCK:
        existing = _RUNNING.get(mission_id)
        if existing and existing.is_alive():
            return False
        if workspace and _busy_locked(workspace, mission_id):
            return False
        orca = factory()

        def work() -> None:
            try:
                orca.run(mission_id)
            except Exception as exc:  # never let a mission stall silently
                _record_crash(orca, mission_id, exc)

        thread = threading.Thread(target=work, name=f"orca-{mission_id}", daemon=True)
        _RUNNING[mission_id] = thread
        _WORKSPACES[mission_id] = workspace
        thread.start()
        return True


# Missions in these states are waiting for someone (or done): a restart never restarts them.
WAITING_STATUSES = {"awaiting_execution_approval", "awaiting_decision", "paused"}


def resume_interrupted(factory: OrcaFactory) -> List[str]:
    """Restart missions the last server process left mid-run (planning, building, reviewing...).
    Each runs in its own thread; at most one per workspace. Returns the resumed mission ids."""
    orca = factory()
    resumed: List[str] = []
    claimed: set = set()
    for mission_id in orca.store.list_ids():
        mission = orca.store.load(mission_id)
        if mission is None or mission.finished or mission.status in WAITING_STATUSES:
            continue
        if mission.workspace_root in claimed:
            continue
        mission.record("resumed_after_restart", status=mission.status)
        orca.store.save(mission)
        if start_background_run(mission_id, factory, mission.workspace_root):
            claimed.add(mission.workspace_root)
            resumed.append(mission_id)
    return resumed


def wait_for(mission_id: str, timeout: Optional[float] = None) -> None:
    """Block until the mission's background run ends (used by checks)."""
    with _LOCK:
        thread = _RUNNING.get(mission_id)
    if thread is not None:
        thread.join(timeout)
