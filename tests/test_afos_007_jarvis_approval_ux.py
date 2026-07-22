from app.platform.services.board_room_agents import run_board_room_deliberation
from app.platform.ui.jarvis_experience import enhance_dashboard_with_jarvis


def test_health_request_gets_tiny_effort_and_decision_actions():
    result = run_board_room_deliberation(
        message='Create a new FastAPI endpoint /health that returns {"status": "ok"} with a unit test.'
    )

    assert result["intent"] == "engineering_execution"
    assert result["guided_action"]["effort_band"] in {"Tiny", "Small"}
    assert result["guided_action"]["estimated_effort"] in {"5–15 minutes", "15–30 minutes"}
    assert [button["label"] for button in result["action_buttons"]] == [
        "Approve Mission",
        "Edit Scope",
        "Reject",
    ]
    assert result["action_buttons"][0]["expects_durable_run"] is True


def test_jarvis_ui_preserves_edit_scope_action_cards():
    html = "<html><head></head><body><section id='board'></section></body></html>"
    enhanced = enhance_dashboard_with_jarvis(html)

    assert "edit scope" in enhanced.lower()
    assert "window.editRecommendedScope" in enhanced
