from __future__ import annotations

from typing import Any

from app.platform.execution.service import create_execution_mission


def create_mission_from_board_room(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message") or payload.get("founder_request") or "").strip()
    if not message:
        message = "Create a governed execution mission from the current Board Room discussion."

    return create_execution_mission(
        {
            "token": payload.get("token"),
            "founder_request": message,
            "title": _title_from_message(message),
        }
    )


def _title_from_message(message: str) -> str:
    words = message.split()
    return " ".join(words[:10]).strip().rstrip(".") or "Execution Mission"
