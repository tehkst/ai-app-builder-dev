"""Run Orca missions in the background so HTTP requests return immediately.

One thread per mission at most; a second request for a mission that is already running is a
no-op. Runs are in-process: if the server restarts mid-mission, the saved state is intact and
the founder resumes it with "Run". An unexpected crash pauses the mission with the error, so it
never silently stalls.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from app.platform.orca.engine import Orca

OrcaFactory = Callable[[], Orca]

_RUNNING: Dict[str, threading.Thread] = {}
_LOCK = threading.Lock()


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


def start_background_run(mission_id: str, factory: OrcaFactory) -> bool:
    """Start running the mission in a thread. Returns False if it is already running."""
    with _LOCK:
        existing = _RUNNING.get(mission_id)
        if existing and existing.is_alive():
            return False
        orca = factory()

        def work() -> None:
            try:
                orca.run(mission_id)
            except Exception as exc:  # never let a mission stall silently
                _record_crash(orca, mission_id, exc)

        thread = threading.Thread(target=work, name=f"orca-{mission_id}", daemon=True)
        _RUNNING[mission_id] = thread
        thread.start()
        return True


def wait_for(mission_id: str, timeout: Optional[float] = None) -> None:
    """Block until the mission's background run ends (used by checks)."""
    with _LOCK:
        thread = _RUNNING.get(mission_id)
    if thread is not None:
        thread.join(timeout)
