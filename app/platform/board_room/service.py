from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.platform.board_room.models import ActionItem, AgendaItem, BoardDecision, BoardMeeting, BoardResolution


def build_board_room_summary() -> dict[str, Any]:
    meeting = BoardMeeting(
        meeting_id="BM-0001",
        title="Company Brain Operating Model Kickoff",
        status="completed",
        chair="Founder",
        participants=["Founder", "CEO", "CTO", "Chief Architect", "Chief Product Officer", "CFO", "Corporate Secretary"],
        agenda=[
            AgendaItem("A-0001", "Company Brain foundation", "CTO", "Establish durable company memory and operating model."),
            AgendaItem("A-0002", "Company Object model", "Chief Architect", "Define universal object language for the Company Graph."),
            AgendaItem("A-0003", "Board Room foundation", "Corporate Secretary", "Define how strategic discussions become decisions and missions."),
        ],
        decisions=[
            BoardDecision("DEC-0001", "The company owns its knowledge", "approved", "Founder", "Company memory belongs to AI Software Factory, not external chats or models."),
            BoardDecision("DEC-0002", "Ideas precede missions", "approved", "Founder", "Vague requests must go through discovery before Engineering begins."),
        ],
        resolutions=[
            BoardResolution("BR-0001", "Establish Company Brain Program", "proposed", "DEC-0001", "Create the Company Brain as the durable operating system for AI Software Factory."),
        ],
        action_items=[
            ActionItem("ACT-0001", "CTO", "Implement Board Room domain foundation.", "in_progress"),
            ActionItem("ACT-0002", "Corporate Secretary", "Prepare Board Room templates and future minutes workflow.", "open"),
        ],
    )
    return {
        "company": "AI Software Factory",
        "product": "Board Room",
        "purpose": "Structured executive governance for meetings, decisions, resolutions, and action items.",
        "meeting": asdict(meeting),
    }
