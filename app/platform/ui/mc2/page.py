"""Mission Control v2 page shell (served at /mission-control/v2).

Structure approved in the redesign prototype v3: a menu (Home, Clients, Customers, Company,
Settings) and a Jarvis panel available on every screen. Served at /mission-control/ui (the default
since stage 5) and /mission-control/v2. The classic page was retired in step 3b; its deeper views
are the Insights pages at /mission-control/insights/<view> (insights.py). Sign-in is built in
(login.py); the session token is shared with those pages through localStorage ("mission_control_token").

Stage 1: shell, Home and the Jarvis panel. Stage 2: Customers. Stage 3: Company. Stage 4: Settings.
"""
from __future__ import annotations

from app.platform.ui.mc2.clients_script import CLIENTS_SCRIPT
from app.platform.ui.mc2.company_script import COMPANY_SCRIPT
from app.platform.ui.mc2.customers_script import CUSTOMERS_SCRIPT
from app.platform.ui.mc2.home_script import HOME_SCRIPT
from app.platform.ui.mc2.jarvis_panel import JARVIS_PANEL_HTML, JARVIS_SCRIPT
from app.platform.ui.mc2.login import LOGIN_HTML, LOGIN_SCRIPT
from app.platform.ui.mc2.settings_script import SETTINGS_SCRIPT
from app.platform.ui.mc2.styles import MC2_CSS

SECTIONS = (("home", "Home"), ("clients", "Clients"), ("customers", "Customers"), ("company", "Company"), ("settings", "Settings"))

_SETTINGS_BODY = """
<section class="mc-card mc-group" aria-labelledby="setAi"><h2 class="mc-h2" id="setAi">AI</h2>
  <p class="mc-empty">The model Jarvis and the AI team use. Keys go under Credentials.</p>
  <div class="mc-fields"><label>Provider<select id="mcAiProvider"></select></label><label>Model<select id="mcAiModel"></select></label>
  <button type="button" class="mc-btn" id="mcAiSave">Save</button></div><p class="mc-status" id="mcAiStatus" aria-live="polite"></p>
  <div class="mc-fields"><label>Second-opinion code review (uses the other provider; one extra AI call per build)
  <select id="mcReview"><option value="on">On</option><option value="off">Off</option></select></label>
  <button type="button" class="mc-btn secondary" id="mcReviewSave">Save</button></div><p class="mc-status" id="mcReviewStatus" aria-live="polite"></p>
</section>
<section class="mc-card mc-group" aria-labelledby="setEmail"><h2 class="mc-h2" id="setEmail">Email</h2>
  <p class="mc-empty">How the platform sends email (sign-up, password reset). The password goes under Credentials.</p>
  <div class="mc-fields"><label>Provider<select id="mcEmailProvider"></select></label><button type="button" class="mc-btn" id="mcEmailSave">Save</button></div>
  <p class="mc-status" id="mcEmailStatus" aria-live="polite"></p>
</section>
<section class="mc-card mc-group" aria-labelledby="setGithub"><h2 class="mc-h2" id="setGithub">GitHub</h2>
  <div class="mc-fields"><button type="button" class="mc-btn secondary" id="mcGithubCheck">Check the GitHub connection</button></div>
  <p class="mc-status" id="mcGithubStatus" aria-live="polite"></p>
  <h3 class="mc-h3">Imported repositories</h3><div id="mcRepos"><p class="mc-empty">Loading…</p></div>
  <form class="mc-fields" id="mcRepoForm"><label>Owner<input id="mcRepoOwner" autocomplete="off" placeholder="e.g. tehkst"></label>
  <label>Repository<input id="mcRepoName" autocomplete="off" placeholder="e.g. my-app"></label><button type="submit" class="mc-btn secondary">Import</button></form>
  <p class="mc-status" id="mcRepoStatus" aria-live="polite"></p>
</section>
<section class="mc-card mc-group" aria-labelledby="setCreds"><h2 class="mc-h2" id="setCreds">Credentials</h2>
  <p class="mc-empty">Encrypted at rest and masked. Revealing one shows it for 30 seconds.</p>
  <div id="mcCreds"><p class="mc-empty">Loading…</p></div>
</section>
<section class="mc-card mc-group" aria-labelledby="setDeploy"><h2 class="mc-h2" id="setDeploy">Deployment</h2>
  <p>Paused: there is no hosting since the Google Cloud project was deleted. Publishing a customer’s app stops at the
  pull request (Customers). Deploy setup comes back here once a new host is chosen.</p>
</section>
<section class="mc-card mc-group" aria-labelledby="setAccount"><h2 class="mc-h2" id="setAccount">Your account</h2>
  <div class="mc-fields"><button type="button" class="mc-btn secondary" id="mcLogout">Log out</button></div>
</section>
"""

_CLIENTS_BODY = """
<form class="mc-card mc-fields" id="mcAddClient" aria-label="Add a client">
  <label>Client name<input id="mcClientName" autocomplete="off" required placeholder="e.g. Kopi Corner"></label>
  <label>Contact (email or Upwork)<input id="mcClientContact" autocomplete="off"></label>
  <button type="submit" class="mc-btn">Add client</button>
</form>
<p class="mc-status" id="mcAddClientStatus" aria-live="polite"></p>
<div class="mc-work">
  <ul class="mc-list" id="mcClientList" aria-label="Clients"><li><p class="mc-empty">Loading…</p></li></ul>
  <section class="mc-card mc-detail" id="mcClientDetail" aria-label="Client detail" aria-live="polite">
    <p class="mc-empty">Select a client to see their code, Health Checks and jobs.</p>
  </section>
</div>
<p class="mc-empty">Health Checks only read the code; nothing from a client's code is run. Clients don't see this
screen. Customers (next tab) are people using the Customer Portal, a separate product.</p>
"""

_CUSTOMERS_BODY = """
<div class="mc-metrics" id="mcMetrics" aria-label="Business numbers"></div>
<section class="mc-section" aria-labelledby="publishTitle">
  <h2 class="mc-h2" id="publishTitle">Waiting for you to publish</h2>
  <div id="mcPublish" class="mc-section" aria-live="polite"><p class="mc-empty">Loading…</p></div>
</section>
<section class="mc-section" aria-labelledby="customersTitle">
  <h2 class="mc-h2" id="customersTitle">All customers</h2>
  <div class="mc-card mc-table-wrap" id="mcCustomerTable"><p class="mc-empty">Loading…</p></div>
  <p class="mc-empty">Customers use their own screen, the Customer Portal, to describe and build their apps.
  This page is your view of them.</p>
</section>
"""

_STEPS = (
    ("1 · You", "Tell Jarvis what you want", "Open Jarvis from any screen and say it in plain words. Jarvis turns it into a proposal."),
    ("2 · You", "Hand it to the AI team", "Confirm the proposal. Changes to this platform itself go to engineering review instead."),
    ("3 · The team (Orca)", "Plan, build, check", "Orca runs the team behind the scenes: the architect plans, builders build, "
     "QA and UX check. Up to 3 tries per task, then it asks you."),
    ("4 · You", "Decide and follow along", "Decisions land in Home → Needs you. Progress and history are in Home → All work."),
)
_INSIGHTS = (
    ("organisation", "Organisation", "Departments, teams and the older role agents"),
    ("memory", "Memory and knowledge", "What the company has learned and decided"),
    ("architecture", "How it’s built", "The architecture map and impact analysis"),
    ("lineage", "Delivery history", "How each mission went from idea to done"),
)
_COMPANY_BODY = (
    '<section class="mc-section" aria-labelledby="howTitle"><h2 class="mc-h2" id="howTitle">How work gets done</h2>'
    '<ol class="mc-steps">' + "".join(
        f'<li class="mc-card"><span>{who}</span><h3>{title}</h3><p>{text}</p></li>' for who, title, text in _STEPS
    ) + '</ol></section>'
    '<section class="mc-section" aria-labelledby="teamTitle"><h2 class="mc-h2" id="teamTitle">Your AI team</h2>'
    '<ul class="mc-team" id="mcTeam" aria-live="polite"><li class="mc-empty">Loading…</li></ul></section>'
    '<section class="mc-section" aria-labelledby="insightsTitle"><h2 class="mc-h2" id="insightsTitle">Insights</h2>'
    '<p class="mc-empty">Deeper views. Open them when you need them.</p>'
    '<ul class="mc-insights">' + "".join(
        f'<li><a class="mc-card" href="/mission-control/insights/{key}">'
        f'<strong>{title}</strong><span>{text}</span></a></li>' for key, title, text in _INSIGHTS
    ) + '</ul></section>'
)

_HOME_BODY = """
<section class="mc-section" aria-labelledby="needsYouTitle">
  <h2 class="mc-h2" id="needsYouTitle">Needs you</h2>
  <div id="mcNeedsYou" class="mc-section" aria-live="polite"><p class="mc-empty">Loading…</p></div>
</section>
<section class="mc-section" aria-labelledby="allWorkTitle">
  <h2 class="mc-h2" id="allWorkTitle">All work</h2>
  <div class="mc-tabs" role="tablist" aria-label="Filter work" id="mcTabs"></div>
  <div class="mc-work">
    <ul class="mc-list" id="mcWorkList" aria-label="Work"></ul>
    <section class="mc-card mc-detail" id="mcDetail" aria-label="Work detail">
      <p class="mc-empty">Select a job to see its plan and progress.</p>
    </section>
  </div>
</section>
"""


def _nav() -> str:
    links = "".join(f'<a href="#{key}" data-mc-nav="{key}">{label}</a>' for key, label in SECTIONS)
    return (
        '<nav class="mc-nav" aria-label="Main"><div class="mc-brand"><strong>AI Software Factory</strong>'
        '<span>Mission Control · owner view</span></div>' + links +
        '<div class="mc-spacer"></div></nav>'
    )


def _section(key: str, label: str) -> str:
    if key == "home":
        head = ('<div><h1>Good to see you, Toni</h1><p id="mcSummary">Loading what needs you…</p></div>')
        body = _HOME_BODY
    elif key == "clients":
        head = ("<div><h1>Clients</h1><p>Businesses whose apps we take over and support: their code, Health Checks "
                "and jobs.</p></div>")
        body = _CLIENTS_BODY
    elif key == "customers":
        head = ("<div><h1>Customers</h1><p>The businesses using AI Software Factory, the apps they’re building, "
                "and what’s waiting for you to publish.</p></div>")
        body = _CUSTOMERS_BODY
    elif key == "company":
        head = "<div><h1>Company</h1><p>Who works here, and how the company is put together.</p></div>"
        body = _COMPANY_BODY
    else:
        head = "<div><h1>Settings</h1><p>How the platform connects to AI, email and GitHub, and the keys it uses.</p></div>"
        body = _SETTINGS_BODY
    return (
        f'<section class="mc-page" id="mc-{key}" data-mc-page="{key}" hidden>'
        f'<header class="mc-head">{head}<button type="button" class="mc-btn mc-open-jarvis">Ask Jarvis</button></header>'
        f"{body}</section>"
    )


def render_mission_control_v2() -> str:
    pages = "".join(_section(key, label) for key, label in SECTIONS)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Mission Control</title>"
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">'
        f"<style>{MC2_CSS}</style></head><body>"
        f'{LOGIN_HTML}<div class="mc-app" id="mcShell" hidden>{_nav()}<main class="mc-main" id="mcMain">{pages}</main>{JARVIS_PANEL_HTML}</div>'
        f"<script>{HOME_SCRIPT}</script><script>{LOGIN_SCRIPT}</script><script>{CUSTOMERS_SCRIPT}</script><script>{CLIENTS_SCRIPT}</script><script>{COMPANY_SCRIPT}</script><script>{SETTINGS_SCRIPT}</script><script>{JARVIS_SCRIPT}</script>"
        "</body></html>"
    )
