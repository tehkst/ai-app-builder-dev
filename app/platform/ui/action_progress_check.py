from __future__ import annotations

from app.platform.ui.founder_dashboard_board_chat import render_board_chat_dashboard
from app.platform.ui.executive_presenter_script import render_executive_presenter_script


def main() -> None:
    html = render_board_chat_dashboard()
    assert "var actionRequestInFlight=false" in html
    assert "if(actionRequestInFlight)return" in html
    assert "Mission Control is working…" in html
    assert "aria-live','polite'" in html
    assert "control.disabled=true" in html
    assert "finishActionProgress(progress,el,succeeded)" in html
    assert "Mission Control could not complete the request safely." in html
    assert "response.headers.get('content-type')" in html
    assert "response.text()" in html
    assert "boundedTechnical" in html
    assert "mission_control_active_run" in html
    assert "activeSession.workflow_run_id=data.workflow_run_id" in html
    assert "resumeMissionLink(s.workflow_run_id)" in html
    assert "renderCurrentMission(data)" in html
    assert "missionPollRunId===runId" in html
    assert "attempt>=120" not in html
    assert "localStorage.setItem('mission_control_active_run',runId)" in html
    assert "restoreActiveSession()" in html
    assert "br_ui_active_session_id" in html
    presenter = render_executive_presenter_script()
    assert "mission.progress_percentage===null?null" in presenter
    assert "typeof mission.progress_percentage==='number'" in presenter
    assert "progress_percentage:mission.progress_percentage||0" not in presenter
    assert "if(value===null)return 'Not linked'" in presenter
    assert "if(value===undefined)return 'Unknown'" in presenter
    assert "action/status" in html
    assert "details.appendChild(summary)" in html
    assert "details.open" not in html
    assert "button.expects_durable_run&&!data.workflow_run_id" in html
    assert "Mission Control did not return a durable workflow run." in html
    assert "durable_lifecycle_contract_error" in html
    assert "The requested action could not provide a lifecycle result." not in html
    print("board room action progress UX ok")


if __name__ == "__main__":
    main()
