"""Mission Control v2 page shell (served at /mission-control/v2).

Structure approved in the redesign prototype v3: a four-item menu (Home, Customers, Company,
Settings) and a Jarvis panel available on every screen. Built alongside the classic page
(/mission-control/ui) and switched over stage by stage; the founder logs in on the classic page
and the session token is shared through localStorage ("mission_control_token").

Stage 1 (this file's first version): shell, Home and the Jarvis panel. Customers, Company and
Settings point to their classic equivalents until their stages land.
"""
from __future__ import annotations

from app.platform.ui.mc2.home_script import HOME_SCRIPT
from app.platform.ui.mc2.jarvis_panel import JARVIS_PANEL_HTML, JARVIS_SCRIPT
from app.platform.ui.mc2.styles import MC2_CSS

SECTIONS = (("home", "Home"), ("customers", "Customers"), ("company", "Company"), ("settings", "Settings"))

_STAGE_NOTE = (
    '<div class="mc-stage"><p style="margin:0 0 10px">This area is being rebuilt in the next stage of the '
    'redesign. Until then, use its current version:</p><a class="mc-btn secondary" href="/mission-control/ui#{target}">'
    'Open {label} in classic Mission Control</a></div>'
)

_SECTION_BODIES = {
    "customers": _STAGE_NOTE.format(target="deployments", label="customers and publish requests"),
    "company": _STAGE_NOTE.format(target="organisation", label="the organisation"),
    "settings": _STAGE_NOTE.format(target="settings", label="settings"),
}

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
        '<div class="mc-spacer"></div><a class="mc-classic" href="/mission-control/ui">Classic Mission Control</a></nav>'
    )


def _section(key: str, label: str) -> str:
    if key == "home":
        head = ('<div><h1>Good to see you, Toni</h1><p id="mcSummary">Loading what needs you…</p></div>')
        body = _HOME_BODY
    else:
        head = f"<div><h1>{label}</h1></div>"
        body = _SECTION_BODIES[key]
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
        f'<div class="mc-app">{_nav()}<main class="mc-main" id="mcMain">{pages}</main>{JARVIS_PANEL_HTML}</div>'
        f"<script>{HOME_SCRIPT}</script><script>{JARVIS_SCRIPT}</script>"
        "</body></html>"
    )
