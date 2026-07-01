from __future__ import annotations

from html import escape

from app.platform.ai_workforce.service import build_workforce_summary
from app.platform.executive_office.service import build_executive_briefing
from app.platform.founder_console.service import build_action_queues, build_console_sections, build_founder_console_summary
from app.platform.knowledge_vault.service import build_knowledge_vault_summary
from app.platform.mission_control.service import build_mission_control_summary


def _card(title: str, value: str, description: str) -> str:
    return f"""
    <section class='card'>
      <div class='card-title'>{escape(title)}</div>
      <div class='card-value'>{escape(value)}</div>
      <p>{escape(description)}</p>
    </section>
    """


def _queue_card(item: dict[str, str]) -> str:
    return f"""
    <article class='queue-card'>
      <div>
        <strong>{escape(item['name'])}</strong>
        <span>{escape(item['status'])}</span>
      </div>
      <p>{escape(item['action'])}</p>
      <code>{escape(item['endpoint'])}</code>
    </article>
    """


def _section_row(item: dict[str, str]) -> str:
    return f"""
    <li>
      <strong>{escape(item['section'])}</strong>
      <span>{escape(item['purpose'])}</span>
      <code>{escape(item['primary_endpoint'])}</code>
    </li>
    """


def render_dashboard() -> str:
    mc = build_mission_control_summary()
    console = build_founder_console_summary()
    exec_briefing = build_executive_briefing()
    workforce = build_workforce_summary()
    vault = build_knowledge_vault_summary()

    cards = "".join(_card(card.title, card.value, card.description) for card in mc.cards)
    queues = "".join(_queue_card(item) for item in build_action_queues())
    sections = "".join(_section_row(item) for item in build_console_sections())
    employees = "".join(
        f"<li><strong>{escape(employee['name'])}</strong><span>{escape(employee['role'])} · {escape(employee['department'])}</span></li>"
        for employee in workforce["employees"]
    )
    knowledge = "".join(
        f"<li><strong>{escape(entry['title'])}</strong><span>{escape(entry['category'])}</span></li>"
        for entry in vault["entries"]
    )
    decisions = "".join(
        f"<li><strong>{escape(item['title'])}</strong><span>{escape(item['recommendation'])}</span></li>"
        for item in exec_briefing["decisions"]
    )

    handover = "Ready" if console["mission_control_primary_workflow"] else "Not ready"
    login = console["login_status"]
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"

    return f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>AI Software Factory · Founder Mission Control</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    body {{ margin: 0; background: #05070d; color: #e8eefc; }}
    .shell {{ display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }}
    aside {{ border-right: 1px solid #1d2638; background: #080b13; padding: 28px; position: sticky; top: 0; height: 100vh; box-sizing: border-box; }}
    main {{ padding: 32px; }}
    .brand {{ font-size: 13px; letter-spacing: .18em; color: #91a4c7; text-transform: uppercase; }}
    h1 {{ margin: 8px 0 4px; font-size: 34px; }}
    h2 {{ margin-top: 36px; font-size: 20px; }}
    .muted {{ color: #91a4c7; }}
    nav a {{ display: block; color: #c8d4ee; text-decoration: none; padding: 10px 0; }}
    .hero {{ display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }}
    .badge {{ border: 1px solid #1e7f4f; background: #09291c; color: #6ee7a8; padding: 8px 12px; border-radius: 999px; font-size: 13px; }}
    .warn {{ border-color: #8a6a1f; background: #2a2109; color: #ffd166; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-top: 24px; }}
    .card, .panel, .queue-card {{ border: 1px solid #1d2638; background: #0b1020; border-radius: 18px; padding: 18px; }}
    .card-title {{ color: #91a4c7; font-size: 13px; }}
    .card-value {{ font-size: 24px; font-weight: 700; margin: 8px 0; }}
    .panel-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .queue-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .queue-card strong {{ display: block; font-size: 16px; }}
    .queue-card span {{ color: #6ee7a8; font-size: 13px; }}
    .queue-card p {{ color: #c8d4ee; min-height: 42px; }}
    code {{ display: inline-block; background: #070a12; border: 1px solid #1d2638; padding: 4px 7px; border-radius: 8px; color: #9cc9ff; font-size: 12px; }}
    ul {{ list-style: none; margin: 0; padding: 0; }}
    li {{ border-top: 1px solid #172033; padding: 12px 0; }}
    li:first-child {{ border-top: 0; }}
    li span {{ display: block; color: #91a4c7; margin: 4px 0; }}
    .status-strip {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }}
    .status-pill {{ border: 1px solid #1d2638; background: #080b13; border-radius: 14px; padding: 14px; }}
    .status-pill span {{ display: block; color: #91a4c7; font-size: 12px; text-transform: uppercase; letter-spacing: .12em; }}
    .status-pill strong {{ display: block; margin-top: 6px; }}
    @media (max-width: 1000px) {{ .shell {{ grid-template-columns: 1fr; }} aside {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid #1d2638; }} .grid, .panel-grid, .queue-grid, .status-strip {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class='shell'>
    <aside>
      <div class='brand'>AI Software Factory</div>
      <h1>Founder Console</h1>
      <p class='muted'>Mission Control operating surface for autonomous software delivery.</p>
      <nav>
        <a href='#queues'>Action Queues</a>
        <a href='#workflow'>Workflow Sections</a>
        <a href='#executive'>Executive Office</a>
        <a href='#workforce'>AI Workforce</a>
        <a href='#knowledge'>Knowledge Vault</a>
      </nav>
    </aside>
    <main>
      <div class='hero'>
        <div>
          <div class='brand'>{escape(mc.environment)} · {escape(mc.region)}</div>
          <h1>Founder Mission Control</h1>
          <p class='muted'>{escape(exec_briefing['headline'])}</p>
        </div>
        <div class='badge'>● {escape(console['status'])}</div>
      </div>
      <div class='status-strip'>
        <div class='status-pill'><span>AI Runtime</span><strong>{escape(ai_status)}</strong></div>
        <div class='status-pill'><span>GCP Handover</span><strong>{escape(handover)}</strong></div>
        <div class='status-pill'><span>Login</span><strong>{escape(login)}</strong></div>
      </div>
      <div class='grid'>{cards}</div>
      <h2 id='queues'>Action Queues</h2>
      <section class='queue-grid'>{queues}</section>
      <h2 id='workflow'>Founder Workflow Sections</h2>
      <section class='panel'><ul>{sections}</ul></section>
      <h2 id='executive'>Executive Office</h2>
      <section class='panel'><ul>{decisions}</ul></section>
      <div class='panel-grid'>
        <section class='panel' id='workforce'><h2>AI Workforce</h2><ul>{employees}</ul></section>
        <section class='panel' id='knowledge'><h2>Knowledge Vault</h2><ul>{knowledge}</ul></section>
      </div>
    </main>
  </div>
</body>
</html>
"""
