from __future__ import annotations

from pathlib import Path
from typing import Any


def _read_meeting() -> str:
    return Path("company/board/meetings/BM-0001.md").read_text(encoding="utf-8")


def _first_value(content: str, heading: str) -> str:
    marker = f"## {heading}"
    start = content.find(marker)
    if start == -1:
        return ""
    lines = content[start + len(marker):].splitlines()
    for line in lines:
        value = line.strip()
        if value.startswith("## "):
            return ""
        if value:
            return value
    return ""


def build_board_room_summary() -> dict[str, Any]:
    content = _read_meeting()
    title = content.splitlines()[0].removeprefix("# ").strip()
    return {
        "company": "AI Software Factory",
        "product": "Board Room",
        "purpose": "Structured executive governance for meetings, decisions, resolutions, and action items.",
        "source": "company/board/meetings/BM-0001.md",
        "meeting": {
            "meeting_id": _first_value(content, "Meeting ID"),
            "title": title.split(": ", 1)[1] if ": " in title else title,
            "status": _first_value(content, "Status"),
            "chair": _first_value(content, "Chair"),
            "participants": [
                "Founder",
                "CEO",
                "CTO",
                "Chief Architect",
                "Chief Product Officer",
                "CFO",
                "Corporate Secretary",
            ],
            "agenda": [],
            "decisions": [],
            "resolutions": [],
            "action_items": [],
        },
    }
