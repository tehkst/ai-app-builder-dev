from __future__ import annotations

from app.platform.constitution.board_room_binding import _attachment_context
from app.platform.ui.jarvis_experience import enhance_dashboard_with_jarvis


def run() -> None:
    source = "<html><head></head><body><div id='board'></div></body></html>"
    rendered = enhance_dashboard_with_jarvis(source)
    required = (
        "Message Jarvis...",
        "jarvisAttachmentInput",
        "pendingAttachments",
        "meaningfulActionCard",
        "review evidence",
        "body.attachments",
        "jarvis_tab_session_v1",
        "jarvis_active_draft_v1",
        "archiveActiveSession",
        "lifecycle_state='archived'",
        "sessionStorage.getItem(TAB_KEY)",
        "localStorage.removeItem(ACTIVE_KEY)",
        "originalNewChat",
    )
    for value in required:
        assert value in rendered, value
    assert rendered.index("<style>") < rendered.index("</head>")
    assert rendered.index("<script>") < rendered.index("</body>")
    assert "if(!sessionStorage.getItem(TAB_KEY))" in rendered
    assert "var originalNewChat=window.newBoardChat" in rendered
    assert "archiveActiveSession();clearDraft();pendingAttachments=[]" in rendered

    context, evidence = _attachment_context(
        {
            "attachments": [
                {
                    "name": "notes.md",
                    "mime_type": "text/markdown",
                    "kind": "text",
                    "size": 14,
                    "content": "Founder evidence",
                },
                {
                    "name": "screen.png",
                    "mime_type": "image/png",
                    "kind": "binary",
                    "size": 2048,
                    "content": "data:image/png;base64,ignored",
                },
            ]
        }
    )
    assert "Founder evidence" in context
    assert "screen.png" in context
    assert len(evidence) == 2
    assert evidence[0]["content_available"] is True
    assert evidence[1]["content_available"] is False
    assert "base64" not in context


if __name__ == "__main__":
    run()
    print("Jarvis experience checks passed")
