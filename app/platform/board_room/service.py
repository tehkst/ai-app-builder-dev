from __future__ import annotations

from pathlib import Path
from typing import Any


def _read_meeting() -> str:
    return Path("company/board/meetings/BM-0001.md").read_text(encoding="utf-8")


def _section(content: str, heading: str) -> str:
    marker = f"## {heading}"
    start = content.find(marker)
    if start == -1:
        return ""
    rest = content[start + len(marker):]
    next_heading = rest.find("\n## ")
    if next_heading >= 0:
        rest = rest[:next_heading]
    return rest.strip()


def _first_value(content: str, heading: str) -> str:
    for line in _section(content, heading).splitlines():
        value = line.strip()
        if value:
            return value
    return ""


def _participants(content: str) -> list[str]:
    rows = []
    for line in _section(content, "Participants").splitlines():
        value = line.strip()
        if value.startswith("- "):
            rows.append(value.removeprefix("- ").strip())
    return rows


def _table(content: str, heading: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in _section(content, heading).splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = [item.strip().lower().replace(" ", "_") for item in lines[0].strip("|").split("|")]
    records: list[dict[str, str]] = []
    for line in lines[2:]:
        values = [item.strip() for item in line.strip("|").split("|")]
        records.append(dict(zip(headers, values)))
    return records


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
            "participants": _participants(content),
            "agenda": _table(content, "Agenda"),
            "decisions": _table(content, "Decisions"),
            "resolutions": _table(content, "Resolutions"),
            "action_items": _table(content, "Action Items"),
        },
    }
