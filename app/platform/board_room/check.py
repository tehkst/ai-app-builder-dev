from __future__ import annotations

from app.platform.board_room.service import build_board_room_summary


def main() -> None:
    summary = build_board_room_summary()
    meeting = summary["meeting"]
    assert summary["company"] == "AI Software Factory"
    assert summary["product"] == "Board Room"
    assert meeting["meeting_id"] == "BM-0001"
    assert len(meeting["participants"]) >= 5
    assert len(meeting["agenda"]) >= 3
    assert len(meeting["decisions"]) >= 2
    assert len(meeting["resolutions"]) >= 1
    assert len(meeting["action_items"]) >= 2
    print("BOARD ROOM DOMAIN CHECK PASSED")


if __name__ == "__main__":
    main()
