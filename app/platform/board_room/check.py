from __future__ import annotations

from app.platform.board_room.service import build_board_room_summary


def main() -> None:
    summary = build_board_room_summary()
    meeting = summary["meeting"]
    assert summary["company"] == "AI Software Factory"
    assert summary["product"] == "Board Room"
    assert summary["source"] == "company/board/meetings/BM-0001.md"
    assert meeting["meeting_id"] == "BM-0001"
    assert meeting["title"] == "Company Brain Operating Model Kickoff"
    assert meeting["status"] == "completed"
    assert meeting["chair"] == "Founder"
    assert len(meeting["participants"]) >= 5
    print("BOARD ROOM DOMAIN CHECK PASSED")


if __name__ == "__main__":
    main()
