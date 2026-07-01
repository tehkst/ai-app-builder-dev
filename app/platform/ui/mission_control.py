from __future__ import annotations

from html import escape

from app.platform.ai_workforce.service import build_workforce_summary
from app.platform.auth.service import build_auth_summary
from app.platform.ci_repair.service import build_ci_repair_summary
from app.platform.executive_office.service import build_executive_briefing
from app.platform.founder_console.service import build_action_queues, build_console_sections, build_founder_console_summary
from app.platform.github_execution.service import build_github_execution_summary
from app.platform.knowledge_vault.service import build_knowledge_vault_summary
from app.platform.mission_control.service import build_mission_control_summary
from app.platform.operating_console.service import build_dashboard_state, build_operating_console_summary
from app.platform.pr_orchestration.service import build_pr_orchestration_summary


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


def _dashboard_tile(item: dict[str, str]) -> str:
    return f"""
    <article class='queue-card'>
      <strong>{escape(item['name'])}</strong>
      <span>{escape(item['status'])}</span>
      <code>{escape(item['endpoint'])}</code>
    </article>
    """


def render_dashboard() -> str:
    mc = build_mission_control_summary()
    console = build_founder_console_summary()
    operating = build_operating_console_summary()
    dashboard = build_dashboard_state()
    auth = build_auth_summary()
    exec_briefing = build_executive_briefing()
    workforce = build_workforce_summary()
    vault = build_knowledge_vault_summary()
    github = build_github_execution_summary()
    ci = build_ci_repair_summary()
    prs = build_pr_orchestration_summary()

    cards = "".join(_card(card.title, card.value, card.description) for card in mc.cards)
    queues = "".join(_queue_card(item) for item in build_action_queues())
    sections = "".join(_section_row(item) for item in build_console_sections())
    tiles = "".join(_dashboard_tile(item) for item in dashboard["tiles"])
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
    login = auth["status"]
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"
    primary_status = operating["handover_status"]

    return f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>AI Software Factory · Founder Operating Console</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    body {{ margin: 0; background: #05070d; color: #e8eefc; }}
    .shell {{ display: grid; grid-template-columns: 290px 1fr; min-height: 100vh; }}
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
    .card, .panel, .queue-card, .chat-box {{ border: 1px solid #1d2638; background: #0b1020; border-radius: 18px; padding: 18px; }}
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
    .status-strip {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }}
    .status-pill {{ border: 1px solid #1d2638; background: #080b13; border-radius: 14px; padding: 14px; }}
    .status-pill span {{ display: block; color: #91a4c7; font-size: 12px; text-transform: uppercase; letter-spacing: .12em; }}
    .status-pill strong {{ display: block; margin-top: 6px; }}
    label {{ display:block; color:#91a4c7; font-size:13px; margin: 12px 0 6px; }}
    input, textarea, select {{ width:100%; box-sizing:border-box; border:1px solid #1d2638; background:#070a12; color:#e8eefc; border-radius:12px; padding:12px; font:inherit; }}
    textarea {{ min-height: 130px; resize: vertical; }}
    button {{ margin-top:12px; border:0; border-radius:12px; padding:12px 16px; background:#2b6df6; color:white; font-weight:700; cursor:pointer; }}
    button.secondary {{ background:#172033; color:#dbe7ff; margin-left:8px; }}
    pre {{ white-space: pre-wrap; background:#070a12; border:1px solid #1d2638; border-radius:12px; padding:14px; color:#c8d4ee; max-height:420px; overflow:auto; }}
    .chat-layout {{ display:grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, .9fr); gap:18px; }}
    @media (max-width: 1000px) {{ .shell {{ grid-template-columns: 1fr; }} aside {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid #1d2638; }} .grid, .panel-grid, .queue-grid, .status-strip, .chat-layout {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class='shell'>
    <aside>
      <div class='brand'>AI Software Factory</div>
      <h1>Founder Console</h1>
      <p class='muted'>Run the company from GCP. Chat, approve, execute, repair, and track work without Swagger.</p>
      <nav>
        <a href='#chat'>Mission Chat</a>
        <a href='#dashboard'>Dashboard</a>
        <a href='#queues'>Action Queues</a>
        <a href='#workflow'>Workflow Sections</a>
        <a href='#executive'>Executive Office</a>
        <a href='#workforce'>AI Workforce</a>
        <a href='/docs'>Swagger fallback</a>
      </nav>
    </aside>
    <main>
      <div class='hero'>
        <div>
          <div class='brand'>{escape(mc.environment)} · {escape(mc.region)}</div>
          <h1>Founder Operating Console</h1>
          <p class='muted'>{escape(primary_status)}</p>
        </div>
        <div class='badge'>● {escape(operating['status'])}</div>
      </div>
      <div class='status-strip'>
        <div class='status-pill'><span>AI Runtime</span><strong>{escape(ai_status)}</strong></div>
        <div class='status-pill'><span>GCP Handover</span><strong>{escape(handover)}</strong></div>
        <div class='status-pill'><span>Login</span><strong>{escape(login)}</strong></div>
        <div class='status-pill'><span>GitHub</span><strong>{escape(str(github.get('status')))}</strong></div>
      </div>

      <h2 id='chat'>Mission Chat</h2>
      <section class='chat-layout'>
        <div class='chat-box'>
          <label>Founder email</label>
          <input id='email' value='founder@ai-software-factory.local' />
          <label>Password</label>
          <input id='password' type='password' placeholder='Set FOUNDER_PASSWORD in Cloud Run Secret Manager' />
          <button onclick='login()'>Login</button><button class='secondary' onclick='logout()'>Logout</button>
          <label>Mission request</label>
          <textarea id='message' placeholder='Example: Implement customer billing module with Stripe, approval workflow, tests, and deployment gates.'></textarea>
          <label>Workflow action</label>
          <select id='action'>
            <option value='create-proposal'>Create proposal only</option>
            <option value='approve-and-plan'>Approve and plan</option>
            <option value='approve-and-start'>Approve, plan, and start</option>
          </select>
          <button onclick='chat()'>Ask AI</button><button class='secondary' onclick='workflow()'>Run Workflow</button>
        </div>
        <div class='chat-box'>
          <strong>Mission Control Response</strong>
          <pre id='result'>Ready. Login, type a mission, then Ask AI or Run Workflow.</pre>
        </div>
      </section>

      <h2 id='dashboard'>Live Dashboard</h2>
      <section class='queue-grid'>{tiles}</section>
      <div class='status-strip'>
        <div class='status-pill'><span>Approvals</span><strong>{escape(str(console['status']))}</strong></div>
        <div class='status-pill'><span>Pull Requests</span><strong>{escape(str(prs.get('status')))}</strong></div>
        <div class='status-pill'><span>CI Repair</span><strong>{escape(str(ci.get('status')))}</strong></div>
        <div class='status-pill'><span>Executor</span><strong>{escape(str(github.get('mode')))}</strong></div>
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
<script>
let token = localStorage.getItem('mission_control_token') || '';
function show(data) {{ document.getElementById('result').textContent = JSON.stringify(data, null, 2); }}
async function post(url, body) {{
  const response = await fetch(url, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(body) }});
  const data = await response.json();
  show(data);
  return data;
}}
async function login() {{
  const data = await post('/mission-control/auth/login', {{ email: document.getElementById('email').value, password: document.getElementById('password').value }});
  if (data.session && data.session.token) {{ token = data.session.token; localStorage.setItem('mission_control_token', token); }}
}}
function logout() {{ token=''; localStorage.removeItem('mission_control_token'); show({{status:'logged-out'}}); }}
async function chat() {{
  await post('/mission-control/operating-console/chat', {{ token, message: document.getElementById('message').value, mode: 'proposal' }});
}}
async function workflow() {{
  await post('/mission-control/operating-console/workflow', {{ token, action: document.getElementById('action').value, message: document.getElementById('message').value }});
}}
</script>
</body>
</html>
"""
