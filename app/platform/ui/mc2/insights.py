"""Insights pages (step 3b): Organisation, Memory, Architecture map and Delivery history, served at
/mission-control/insights/<view> now that the classic Mission Control page is retired.

Each page reuses its existing section markup and script (they call their own founder-only APIs with
the shared session token) inside a light shell matching Mission Control, with a small compatibility
stylesheet for the classic class names and colour variables.
"""
from __future__ import annotations

from html import escape
from typing import Callable, Dict, Tuple

from app.platform.ui.architecture_graph_script import render_architecture_graph_script
from app.platform.ui.cognitive_memory_script import MEMORY_SECTION, render_cognitive_memory_script
from app.platform.ui.delivery_lineage_script import LINEAGE_SECTION, render_delivery_lineage_script
from app.platform.ui.founder_dashboard_stable import ARCHITECTURE_SECTION
from app.platform.ui.mc2.styles import MC2_CSS
from app.platform.ui.organisation_console_script import ORGANISATION_SECTION, render_organisation_console_script

# view -> (title, one-line description, section markup, script renderer, start-up JS run after load)
INSIGHTS: Dict[str, Tuple[str, str, str, Callable[[], str], str]] = {
    "organisation": ("Organisation", "Departments, teams and the older role agents", ORGANISATION_SECTION,
                     render_organisation_console_script, ""),
    "memory": ("Memory and knowledge", "What the company has learned and decided", MEMORY_SECTION,
               render_cognitive_memory_script, ""),
    "architecture": ("How it's built", "The architecture map and impact analysis", ARCHITECTURE_SECTION,
                     render_architecture_graph_script, "var b=document.getElementById('akgLoad');if(b)b.click();"),
    "lineage": ("Delivery history", "How each mission went from idea to done", LINEAGE_SECTION,
                render_delivery_lineage_script, "if(window.loadDeliveryLineage)window.loadDeliveryLineage();"),
}

# The classic sections use these class names and colour variables; map them onto the light theme.
COMPAT_CSS = r"""
.mc-insight{--line:var(--line-soft);--text:var(--ink);--blue:var(--accent);--purple:var(--accent-ink);--green:var(--done);
color:var(--ink)}
.mc-insight .section{display:block}
.mc-insight .card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:14px}
.mc-insight .hero h2{margin:0 0 6px;font-size:24px}
.mc-insight .muted,.mc-insight .small{color:var(--muted)}
.mc-insight .grid,.mc-insight .grid4,.mc-insight .layout{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.mc-insight .row{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--line-soft);padding:10px 0}
.mc-insight .tag{display:inline-flex;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:600;background:var(--accent-soft);color:var(--accent-ink)}
.mc-insight .kpi{font-size:26px;font-weight:700}.mc-insight .good{color:var(--done);font-weight:600}.mc-insight .warn{color:var(--needs);font-weight:600}
.mc-insight .error{color:var(--stuck)}.mc-insight .actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.mc-insight button{min-height:40px;border-radius:10px;padding:0 14px;font-weight:600;cursor:pointer}
.mc-insight .primary{background:var(--accent);color:#fff;border:0}.mc-insight .secondary{background:var(--surface);color:var(--ink);border:1px solid var(--field)}
.mc-insight input,.mc-insight select,.mc-insight textarea{border:1px solid var(--field);border-radius:10px;padding:10px;background:#fff;color:var(--ink);font:inherit}
.mc-insight pre{white-space:pre-wrap;background:var(--ground);border:1px solid var(--line-soft);border-radius:10px;padding:12px;overflow:auto}
/* Hard-coded dark surfaces inside the classic sections, mapped to the light palette. */
.mc-insight :is(.org-metric,.org-node,.organisation-canvas,.team-block,.worker-drawer,.worker-mini,.directory-row,
.drawer-head,.icon-control,.notice,.mem-fact,.mem-episode,.mem-contradiction,.akg-node,.akg-svg,.lineage-entry){
background:var(--surface);color:var(--ink);border-color:var(--line)}
.mc-insight :is(.directory-row:hover,.directory-row:focus-visible){background:var(--accent-soft)}
.mc-insight .notice{background:var(--accent-soft);color:var(--accent-ink)}
.mc-insight .agent-avatar{background:var(--accent-soft);color:var(--accent-ink)}
.mc-insight :is(.org-metric,.org-node,.worker-mini,.mem-fact,.mem-episode,.lineage-entry,.akg-node) :is(strong,b,h3,h4,.value,.kpi){color:var(--ink)}
.mc-insight :is(.message-panel textarea,.memory-shell input,.memory-shell textarea){background:#fff;color:var(--ink);border-color:var(--field)}
.mc-insight-bar{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;padding:14px 24px;background:var(--surface);border-bottom:1px solid var(--line)}
.mc-insight-bar a{text-decoration:none;font-weight:600}.mc-insight-bar a[aria-current="page"]{color:var(--ink)}
.mc-insight-main{max-width:1200px;margin:0 auto;padding:24px 16px 48px}
"""


def render_insight(view: str) -> str:
    title, description, section, script, start = INSIGHTS[view]
    links = "".join(
        f'<a href="/mission-control/insights/{key}"{" aria-current=page" if key == view else ""}>{escape(item[0])}</a>'
        for key, item in INSIGHTS.items())
    views = ",".join(f"'{key}'" for key in INSIGHTS)
    boot = (
        # Signed out, or the session expired: back to Mission Control, which shows the sign-in screen.
        "<script>(function(){var t='';try{t=localStorage.getItem('mission_control_token')||''}catch(e){}"
        "function out(){window.location.replace('/mission-control/ui')}"
        "if(!t){out();return}"
        "fetch('/mission-control/auth/session',{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({token:t})}).then(function(r){return r.json()}).then(function(s){if(!s.authenticated)out()})"
        ".catch(function(){});"
        f"if(location.hash!=='#{view}')history.replaceState(null,'','#{view}');"
        # The reused classic scripts call showSection(); route it between the Insights pages.
        f"var VIEWS=[{views}];"
        "function go(v,q){if(VIEWS.indexOf(v)<0)return false;window.location.href='/mission-control/insights/'+v+(q?'?'+q:'');return true}"
        "window.showSection=function(v){go(String(v||'').replace(/^#/,''))};"
        # Organisation 'Open evidence' buttons: carry the mission/workflow/target to the other page.
        "document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-org-link]');if(!b)return;"
        "var v=String(b.dataset.orgLink||'').replace(/^#/,''),q=new URLSearchParams();"
        "if(b.dataset.missionId)q.set('mission',b.dataset.missionId);if(b.dataset.workflowId)q.set('workflow',b.dataset.workflowId);"
        "if(b.dataset.architectureTarget)q.set('target',b.dataset.architectureTarget);"
        "e.preventDefault();e.stopImmediatePropagation();go(v,q.toString())},true);"
        "})();</script>"
    )
    # Fill fields handed over from another Insights page before the page's own start-up runs.
    prefill = ("var q=new URLSearchParams(location.search);[['lineageMissionId','mission'],['lineageWorkflowId','workflow'],"
               "['akgImpactTarget','target']].forEach(function(p){var el=document.getElementById(p[0]);"
               "if(el&&q.get(p[1]))el.value=q.get(p[1])});")
    after = f"<script>window.addEventListener('load',function(){{{prefill}{start}}});</script>"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)} · Mission Control</title>"
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">'
        f"<style>{MC2_CSS}{COMPAT_CSS}</style>{boot}</head><body>"
        f'<nav class="mc-insight-bar" aria-label="Insights"><a href="/mission-control/ui#company">← Mission Control</a>{links}</nav>'
        f'<main class="mc-insight-main mc-insight"><p class="mc-empty">{escape(description)}</p>{section}</main>'
        f"{script()}{after}</body></html>"
    )
