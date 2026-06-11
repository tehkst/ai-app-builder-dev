from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
    persist_workflow_result,
)


GYM_DEMO_SAFETY_MODE = "db_preview_only_demo_no_runtime_execution"


def _safe_flags() -> Dict[str, bool]:
    return {
        "demo_seeded": True,
        "single_user_activity_recorded": True,
        "db_preview_only": True,
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "deployment_performed": False,
    }


def _manager_html() -> str:
    return """<!doctype html>
<html><head><meta charset="utf-8"><title>Gym Manager Admin</title></head>
<body>
<main>
<h1>Gym Manager Admin</h1>
<p>Capacity control: 24 total spaces, 18 booked, 6 available.</p>
<section><h2>Today</h2><ul>
<li>07:00 - 08:00: 8 / 12 booked</li>
<li>12:00 - 13:00: 10 / 12 booked</li>
<li>18:00 - 19:00: 12 / 12 booked - waitlist open</li>
</ul></section>
<section><h2>Manager actions</h2>
<button>Adjust slot capacity</button><button>View member bookings</button>
</section>
</main>
</body></html>"""


def _goer_html() -> str:
    return """<!doctype html>
<html><head><meta charset="utf-8"><title>Gym Goer Booking</title></head>
<body>
<main>
<h1>Book Your Gym Slot</h1>
<p>Choose a time before coming to the gym so the manager can control space.</p>
<section><h2>Available slots</h2><ul>
<li>07:00 - 08:00: 4 spaces left <button>Book</button></li>
<li>12:00 - 13:00: 2 spaces left <button>Book</button></li>
<li>20:00 - 21:00: 9 spaces left <button>Book</button></li>
</ul></section>
<section><h2>My booking</h2><p>No active booking selected.</p></section>
</main>
</body></html>"""


def _readme() -> str:
    return """# Gym Booking App Demo

This DB-preview demo models one SaaS user creating a gym slot booking app.

Surfaces:
- `manager.html`: gym manager admin view for slot capacity and bookings.
- `gym-goer.html`: member-facing booking view for available exercise slots.

Safety:
- No generated files are written to disk by this route.
- No generated code is executed by this route.
"""


def _generated_files() -> List[Dict[str, Any]]:
    return [
        {
            "path": "manager.html",
            "language": "html",
            "purpose": "Gym manager admin view for capacity-controlled slots.",
            "content_preview": _manager_html(),
            "write_status": "preview_only",
        },
        {
            "path": "gym-goer.html",
            "language": "html",
            "purpose": "Gym goer booking view for reserving exercise time slots.",
            "content_preview": _goer_html(),
            "write_status": "preview_only",
        },
        {
            "path": "README.md",
            "language": "markdown",
            "purpose": "Demo app handoff notes and safety statement.",
            "content_preview": _readme(),
            "write_status": "preview_only",
        },
    ]


def _step_run(step_id: str, title: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "step_run_id": f"gym_demo_{step_id}_{uuid4().hex[:8]}",
        "step_id": step_id,
        "title": title,
        "required_capability": "static_preview_generation",
        "selected_agent": {"agent_id": "gym_booking_demo_agent"},
        "status": "completed",
        "output": {
            "bridge_result": {
                "handler_result": {
                    "success": True,
                    "message": title,
                    "generated_files": files,
                }
            }
        },
    }


def create_gym_booking_demo_run(
    db: Session,
    *,
    created_by: str = "gym_app_user_001",
) -> Dict[str, Any]:
    workflow_run_id = f"gym_booking_demo_{uuid4().hex[:12]}"
    files = _generated_files()
    result = {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "workflow_name": "Gym Booking App Demo",
        "status": "completed",
        "plan_status": "demo_preview_ready",
        "simulation": True,
        "step_count": 3,
        "completed_step_count": 3,
        "blocked_step_count": 0,
        "failed_step_count": 0,
        "step_runs": [
            _step_run("user_activity", "1 user is creating Gym Booking App", []),
            _step_run("manager_surface", "Generated gym manager admin view", [files[0]]),
            _step_run("goer_surface", "Generated gym goer booking view", files[1:]),
        ],
    }
    persist_workflow_result(db, result=result)
    detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
    persisted = persist_generated_files_for_workflow(db, detail)
    return {
        "success": True,
        "safety_mode": GYM_DEMO_SAFETY_MODE,
        "workflow_run_id": workflow_run_id,
        "user_activity": {
            "active_user_count": 1,
            "created_by": created_by,
            "activity": "creating Gym Booking App",
        },
        "generated_surfaces": ["manager.html", "gym-goer.html"],
        "manager_preview": "manager.html",
        "gym_goer_preview": "gym-goer.html",
        "generated_file_persistence": persisted,
        "safety_flags": _safe_flags(),
    }
