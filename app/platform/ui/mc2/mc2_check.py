"""Check for Mission Control v2 (stages 1-5): the route serves the redesigned shell from the production
app, the structure matches the approved prototype, the customers API is founder-only and joins
customers to their apps correctly, and the scripts parse."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.customers_overview.service import app_stage, build_customers_overview, saas_stage
from app.platform.server import app
from app.platform.ui.mc2.clients_script import CLIENTS_SCRIPT
from app.platform.ui.mc2.company_script import COMPANY_SCRIPT
from app.platform.ui.mc2.customers_script import CUSTOMERS_SCRIPT
from app.platform.ui.mc2.settings_script import SETTINGS_SCRIPT
from app.platform.ui.mc2.home_script import HOME_SCRIPT
from app.platform.ui.mc2.jarvis_panel import JARVIS_SCRIPT
from app.platform.ui.mc2.login import LOGIN_SCRIPT
from app.platform.ui.mc2.page import SECTIONS


def check_route_and_structure() -> None:
    client = TestClient(app)
    response = client.get("/mission-control/ui")
    assert response.status_code == 200 and "text/html" in response.headers["content-type"], response.status_code
    html = response.text
    assert client.get("/mission-control/v2").text == html, "/mission-control/v2 stays as an alias"
    assert 'id="mcLogin"' in html and '<div class="mc-app" id="mcShell" hidden>' in html, "sign-in first, app hidden"
    # Step 3b: the classic page is retired; its Insights views live on their own light pages.
    assert client.get("/mission-control/classic").status_code == 404, "the classic page is retired"
    assert client.get("/mission-control/insights/unknown").status_code == 404
    for key in ("organisation", "memory", "architecture", "lineage"):
        page = client.get(f"/mission-control/insights/{key}")
        assert page.status_code == 200 and 'class="mc-insight-bar"' in page.text, key
        assert 'href="/mission-control/ui#company"' in page.text and "/mission-control/classic" not in page.text, key
        assert "/mission-control/auth/session" in page.text, f"{key} must check the session is still valid"
        assert "window.showSection=function" in page.text and "[data-org-link]" in page.text, f"{key} routes evidence links"
    nav = re.findall(r'data-mc-nav="([a-z]+)">([^<]+)<', html)
    assert nav == [("home", "Home"), ("clients", "Clients"), ("customers", "Customers"), ("company", "Company"),
                   ("settings", "Settings")], nav
    assert [key for key, _ in SECTIONS] == ["home", "clients", "customers", "company", "settings"]
    assert html.count('class="mc-btn mc-open-jarvis"') == 5, "every screen needs an Ask Jarvis button"
    assert html.count("<textarea") == 1, "Jarvis must be the only place to type"
    for marker in ('id="mcNeedsYou"', 'id="mcWorkList"', 'id="mcDetail"', 'id="mcJarvis"',
                   'id="mcMetrics"', 'id="mcPublish"', 'id="mcCustomerTable"', 'id="mcTeam"', 'class="mc-steps"',
                   'id="mcAiProvider"', 'id="mcEmailProvider"', 'id="mcGithubCheck"', 'id="mcCreds"', 'id="mcLogout"',
                   'id="mcAddClient"', 'id="mcClientList"', 'id="mcClientDetail"', 'id="mcAlertList"'):
        assert marker in html, marker
    for key in ("organisation", "memory", "architecture", "lineage"):
        marker = f'href="/mission-control/insights/{key}"'
        assert marker in html, marker
    assert "/mission-control/classic" not in html, "no links to the retired classic page"
    assert "mc-stage" not in html, "every section is rebuilt; no stage notes left"
    for removed in ("Projects", "Workflows", "Executions", "Board Room</"):
        assert removed not in re.sub(r"<script>.*?</script>", "", html, flags=re.S), f"{removed} should be gone"


def check_script_contracts() -> None:
    for endpoint in ("/mission-control/orca/missions", "/mission-control/orca/mission",
                     "/mission-control/publish-requests/list", "/mission-control/auth/session"):
        assert endpoint in HOME_SCRIPT, endpoint
    assert "/mission-control/operating-console/chat" in JARVIS_SCRIPT
    assert "conversation_history" in JARVIS_SCRIPT and "board_room_response" in JARVIS_SCRIPT
    assert "window.openOrcaMission" in JARVIS_SCRIPT and "window.confirm" in JARVIS_SCRIPT, "hand-off needs founder confirm"
    assert "indexOf('/mission-control/')!==0" in JARVIS_SCRIPT, "post buttons must stay inside Mission Control"
    for name in ("requestUiUxIteration", "approveUiUxChange", "mergeUiUxPullRequest"):
        assert "window." + name + "=" in JARVIS_SCRIPT and "'" + name + "'" in JARVIS_SCRIPT, f"{name} handler missing"
    for phrase in ("I APPROVE GITHUB EXECUTION", "I APPROVE PR MERGE"):
        assert phrase in JARVIS_SCRIPT, f"{phrase} gate missing"
    assert "ui#deployments" not in HOME_SCRIPT and 'href="#customers"' in HOME_SCRIPT, "publish review now lives in Customers"
    for endpoint in ("/mission-control/business-metrics", "/mission-control/customers/list", "/mission-control/publish-requests/"):
        assert endpoint in CUSTOMERS_SCRIPT, endpoint
    assert "I APPROVE GITHUB EXECUTION" in CUSTOMERS_SCRIPT and "window.confirm" in CUSTOMERS_SCRIPT, "publish gates"
    assert "deployment/execute" not in CUSTOMERS_SCRIPT, "no deploy until there is a host"
    assert "/mission-control/orca/workforce" in COMPANY_SCRIPT and "esc(p.why)" in COMPANY_SCRIPT
    assert "MC.onShow.company" in COMPANY_SCRIPT and "MC.onShow.customers" in CUSTOMERS_SCRIPT
    for endpoint in ("/mission-control/runtime/ai-provider", "/mission-control/runtime/smtp-provider",
                     "/mission-control/runtime/independent-review", "/mission-control/credentials/list",
                     "/mission-control/credentials/save", "/mission-control/github/health", "/mission-control/repo-import/"):
        assert endpoint in SETTINGS_SCRIPT, endpoint
    assert "window.confirm('Show this secret" in SETTINGS_SCRIPT and "30000" in SETTINGS_SCRIPT, "reveal needs a confirm and hides again"
    assert 'type="password"' in SETTINGS_SCRIPT, "new secrets are typed into password fields"
    assert "/mission-control/auth/login" in LOGIN_SCRIPT and "/mission-control/auth/forgot-password" in LOGIN_SCRIPT
    assert "MC.start()" in LOGIN_SCRIPT and "MC.start=async function" in HOME_SCRIPT
    assert "window.location.href='/mission-control/ui'" not in HOME_SCRIPT + SETTINGS_SCRIPT, "no redirect loop to itself"
    assert "/mission-control/execution" not in HOME_SCRIPT, "platform missions moved to the dev workflow"
    assert "/mission-control/classic" not in HOME_SCRIPT + JARVIS_SCRIPT, "no links to the retired classic page"
    assert "window.location.href='/mission-control/insights/'+b.target" in JARVIS_SCRIPT, "show_section opens Insights"
    assert "RETIRED_POSTS" in JARVIS_SCRIPT and "'/mission-control/github-merge'" in JARVIS_SCRIPT, "old pipeline buttons hidden"
    for name in ("addInlineNote", "saveCurrentSession", "editRecommendedScope"):
        assert "window." + name + "=" in JARVIS_SCRIPT and "'" + name + "'" in JARVIS_SCRIPT, f"{name} helper missing"
    assert "state.selected!==key" in HOME_SCRIPT, "stale mission details must be discarded"
    for endpoint in ("/mission-control/clients/", "/mission-control/clients/report"):
        assert endpoint in CLIENTS_SCRIPT, endpoint
    assert "if(state.selected!==key)return;" in CLIENTS_SCRIPT, "stale client details must be discarded"
    for marker in ("'start-work'", "client_consent:true", "ai_provider:state.provider", "window.confirm('The AI team will work on a copy",
                   "Only continue if", "agreed to that.'+termsText()", "terms_version:state.terms&&state.terms.version", "'work-changes'", "esc(ch.diff)", "esc(f.path)", "esc(m.paused_reason)"):
        assert marker in CLIENTS_SCRIPT, f"client work: {marker}"
    assert "m.client?'Client: '+m.client" in HOME_SCRIPT, "client missions are labelled in Home"
    assert "MC.costText=function" in HOME_SCRIPT and "MC.costText(m.cost)" in HOME_SCRIPT, "mission AI cost in Home"
    assert "MC.costText(m.cost)" in CLIENTS_SCRIPT and "MC.costText(a.cost)" in CLIENTS_SCRIPT, "job and Audit AI cost"
    assert "h.kind==='security_verdict'?'security review'" in HOME_SCRIPT
    assert "'needs '+t.depends_on.join(', ')" in HOME_SCRIPT, "task dependencies shown"
    for marker in ("call('alert-sweep'", "call('security-alerts')", "esc(a.title)", "esc(r.reason)", "safeUrl(a.source)",
                   'rel="noopener noreferrer"', "data-alert-job"):
        assert marker in CLIENTS_SCRIPT, f"security alerts: {marker}"
    assert 'class="mc-work"' not in CLIENTS_SCRIPT, "mc-work is the page layout (list beside detail), not a job panel"
    assert "questionCard(m)" in HOME_SCRIPT and "esc(q)" in HOME_SCRIPT and "calls.answer=['answer'" in HOME_SCRIPT, "decision questions"
    assert "awaiting_decision:['Questions for you in Home'" in CLIENTS_SCRIPT
    assert "function headline(goal)" in HOME_SCRIPT and "esc(headline(m.goal))" in HOME_SCRIPT and "title:m.goal" not in HOME_SCRIPT
    assert "liveHtml(m)" in HOME_SCRIPT and "esc(a.detail)" in HOME_SCRIPT and "'Now: '+m.now" in HOME_SCRIPT, "live progress"
    for marker in ("call('deliver'", "confirm_repository:typed.trim()", "typed.trim()!==target", "window.prompt(send.dataset.kind==='branch'?",
                   "'This adds one new branch to the git repository in '", "'This pushes one new branch to '", "esc(br.branch)",
                   "'/mission-control/clients/patch'", "esc(pr.url)", 'rel="noopener noreferrer"', "accept_unverified"):
        assert marker in CLIENTS_SCRIPT, f"client delivery: {marker}"
    for marker in ("call('run-audit'", "client_consent:true,ai_provider:state.provider", "window.confirm('The Code Auditor will read",
                   "'/mission-control/clients/audit-report'", "esc(a.summary)", "esc(f.title)", "Not verified", "call('add-job'"):
        assert marker in CLIENTS_SCRIPT, f"audit: {marker}"
    for marker in ("Handover note for the client", "esc(h.summary)", "esc(x)", "esc(h.error)"):
        assert marker in CLIENTS_SCRIPT, f"handover: {marker}"
    assert "MC.onShow.clients" in CLIENTS_SCRIPT and "esc(b.source)" in CLIENTS_SCRIPT and "esc(c.name)" in CLIENTS_SCRIPT
    assert "esc(m.text)" in JARVIS_SCRIPT and "esc(i.title)" in HOME_SCRIPT and "esc(hist)" in HOME_SCRIPT


def check_javascript_parses() -> None:
    node = shutil.which("node")
    if node is None:
        print("  (node not installed: JavaScript syntax check skipped)")
        return
    for name, source in (("home", HOME_SCRIPT), ("customers", CUSTOMERS_SCRIPT), ("clients", CLIENTS_SCRIPT), ("company", COMPANY_SCRIPT), ("settings", SETTINGS_SCRIPT), ("login", LOGIN_SCRIPT), ("jarvis", JARVIS_SCRIPT)):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(source)
        result = subprocess.run([node, "--check", handle.name], capture_output=True, text=True)
        Path(handle.name).unlink()
        assert result.returncode == 0, f"{name} script has a syntax error:\n{result.stderr}"


def check_customers_api() -> None:
    client = TestClient(app)
    assert client.post("/mission-control/customers/list", json={}).json()["status"] == "unauthorized"
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    ready = client.post("/mission-control/customers/list", json={"token": token}).json()
    assert ready["status"] in {"ready", "unavailable"} and ready["contract"] == "customers-overview-v1", ready
    published = {status: app_stage({"publish_status": status, "workflow_run_id": "w"}, "running")
                 for status in ("live", "pr_created", "requested", "approved", "rejected")}
    assert published == {"live": "live", "pr_created": "published, PR open", "requested": "waiting to publish",
                         "approved": "waiting to publish", "rejected": "publish declined"}, published
    by_run = {run: app_stage({"publish_status": "not_requested", "workflow_run_id": "w"}, run)
              for run in ("running", "completed", "failed", None)}
    assert by_run == {"running": "building", "completed": "built, not published", "failed": "build failed",
                      None: "build status unknown"}, "a finished or missing run must not count as building"
    assert app_stage({"publish_status": "not_requested"}) == "scoping"
    assert [saas_stage(s) for s in ("live", "engineering", "failed", "draft")] == ["live", "building", "build failed", "scoping"]
    customers = [
        {"organization_id": "o1", "name": "Acme", "plan": "pro", "created_at": "2026-10-01T00:00:00",
         "updated_at": "2026-10-01T00:00:00", "members": [{"user_id": "u1", "email": "a@example.com"}]},
        {"organization_id": "o2", "name": "Quiet Co", "plan": "free", "created_at": "2026-09-01T00:00:00",
         "updated_at": "2026-09-01T00:00:00", "members": []},
    ]
    apps = [
        {"owner": "u1", "app_id": "S1", "scoping_request_id": "S1", "source": "scoping", "name": "Bookings",
         "stage": "waiting to publish", "updated_at": "2026-10-10T00:00:00"},
        {"owner": "u1", "app_id": "run-1", "scoping_request_id": None, "source": "saas_builder", "name": "Shop",
         "stage": "building", "live_url": None, "updated_at": "2026-10-05T00:00:00"},
        {"owner": "stranger", "app_id": "S2", "source": "scoping", "name": "Orphan", "stage": "scoping"},
    ]
    view = build_customers_overview(customers, apps)
    assert [c["name"] for c in view["customers"]] == ["Acme", "Quiet Co"], "most recent activity first"
    acme = view["customers"][0]
    assert acme["last_activity"] == "2026-10-10T00:00:00" and acme["member_count"] == 1
    assert [(a["name"], a["stage"]) for a in acme["apps"]] == [("Bookings", "waiting to publish"), ("Shop", "building")]
    assert all("owner" not in a for a in acme["apps"])
    assert view["apps_without_customer"] == 1 and view["apps_being_built"] == 1
    assert "a@example.com" not in str(view), "member emails stay out of the overview"


def check_settings_saves_are_founder_only() -> None:
    from app.platform.runtime.provider_router import provider_status

    client = TestClient(app)
    before = provider_status()["provider"]
    other = "deepseek" if before == "openai" else "openai"
    for path, body in (("ai-provider", {"provider": other}), ("smtp-provider", {"provider": "gmail"}),
                       ("independent-review", {"enabled": False})):
        refused = client.post(f"/mission-control/runtime/{path}", json=body).json()
        assert refused["status"] == "unauthorized", (path, refused)
    assert provider_status()["provider"] == before, "an anonymous save must not change the AI provider"
    status = client.get("/mission-control/runtime/ai-provider").json()
    assert set(status["supported_models"]) == {"openai", "deepseek"}, status.get("supported_models")


def main() -> None:
    check_route_and_structure()
    check_settings_saves_are_founder_only()
    check_script_contracts()
    check_customers_api()
    check_javascript_parses()
    print("MISSION CONTROL V2 CHECK PASSED")


if __name__ == "__main__":
    main()
