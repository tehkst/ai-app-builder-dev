from __future__ import annotations

from app.platform.ui.founder_dashboard_board_chat import render_board_chat_dashboard


def main() -> None:
    html = render_board_chat_dashboard()
    assert "var actionRequestInFlight=false" in html
    assert "if(actionRequestInFlight)return" in html
    assert "Mission Control is working…" in html
    assert "aria-live','polite'" in html
    assert "control.disabled=true" in html
    assert "finishActionProgress(progress,el,succeeded)" in html
    assert "Action failed: "+"'+e" in html
    assert "details.appendChild(summary)" in html
    assert "details.open" not in html
    print("board room action progress UX ok")


if __name__ == "__main__":
    main()
