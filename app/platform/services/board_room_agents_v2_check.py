from __future__ import annotations

from app.platform.services.board_room_agents import format_deliberation_markdown, run_board_room_deliberation


def main() -> None:
    result = run_board_room_deliberation(message="Implement the approved mission", db=None)

    assert result["version"] == "executive-board-room-v2"
    assert result["mode"] == "true_multi_agent_board_room"
    assert len(result["contributors"]) == len(result["agents"])
    assert result["guided_action"]["key"] == "approve_mission"
    assert result["guided_action"]["workflow_type"] == "implementation"
    assert result["governance"]["founder_approval_required"] is True
    assert result["governance"]["execution_allowed"] is False
    assert result["state_authorities"]["workflow"] == "existing_founder_workflow_engine"
    assert result["state_authorities"]["mission"] == "existing_mission_pipeline"
    assert result["creates_parallel_capability"] is False
    assert result["evidence"][0]["status"] == "unavailable"

    roadmap = run_board_room_deliberation(message="Review the architecture and produce a roadmap", db=None)
    assert roadmap["guided_action"]["key"] == "generate_architecture_roadmap"
    assert roadmap["guided_action"]["workflow_type"] == "roadmap"

    discussion = run_board_room_deliberation(message="Discuss fundraising strategy", db=None)
    assert discussion["guided_action"]["key"] == "continue_discussion"
    assert discussion["guided_action"]["requires_workflow"] is False

    markdown = format_deliberation_markdown(result)
    for section in (
        "Executive Board Room v2",
        "Evidence",
        "Executive Contributors",
        "Synthesized Decision",
        "Risks",
        "Governance",
        "Guided Next Action",
    ):
        assert section in markdown

    print("AFOS-003 EXECUTIVE BOARD ROOM V2 CHECK PASSED")


if __name__ == "__main__":
    main()
