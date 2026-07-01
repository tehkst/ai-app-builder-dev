from __future__ import annotations

from html import escape

from app.platform.auth.service import build_auth_summary
from app.platform.ci_repair.service import build_ci_repair_summary
from app.platform.founder_console.service import build_founder_console_summary
from app.platform.github_execution.service import build_github_execution_summary
from app.platform.mission_control.service import build_mission_control_summary
from app.platform.operating_console.service import build_board_room_state, build_dashboard_state, build_operating_console_summary
from app.platform.pr_orchestration.service import build_pr_orchestration_summary


def _dashboard_tile(item: dict[str, str]) -> str:
    return f"""
    <article class='tile'>
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
    github = build_github_execution_summary()
    ci = build_ci_repair_summary()
    prs = build_pr_orchestration_summary()
    board_room = build_board_room_state()

    tiles = "".join(_dashboard_tile(item) for item in dashboard["tiles"])
    roles = "".join(f"<span class='role'>{escape(role)}</span>" for role in board_room["roles"])
    agenda = "".join(f"<li>{escape(item)}</li>" for item in board_room["default_agenda"])
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"

    return f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>AI Software Factory · Platform Admin</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; background: radial-gradient(circle at top left, #123067 0, #05070d 34%, #04050a 100%); color: #e8eefc; }}
    .login-screen {{ min-height: 100vh; display: grid; place-items: center; padding: 28px; }}
    .login-card {{ width: min(480px, 100%); border: 1px solid #1d2638; background: rgba(8, 11, 19, .92); border-radius: 26px; padding: 30px; box-shadow: 0 30px 90px rgba(0,0,0,.4); }}
    .brand {{ font-size: 12px; letter-spacing: .18em; color: #91a4c7; text-transform: uppercase; }}
    h1 {{ margin: 10px 0 8px; font-size: 34px; }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    p, .muted {{ color: #91a4c7; }}
    label {{ display:block; color:#91a4c7; font-size:13px; margin: 14px 0 6px; }}
    input, textarea, select {{ width:100%; border:1px solid #1d2638; background:#070a12; color:#e8eefc; border-radius:14px; padding:13px; font:inherit; }}
    textarea {{ min-height: 170px; resize: vertical; line-height: 1.45; }}
    button {{ margin-top:14px; border:0; border-radius:14px; padding:13px 17px; background:#2b6df6; color:white; font-weight:800; cursor:pointer; }}
    button.secondary {{ background:#172033; color:#dbe7ff; margin-left:8px; }}
    button.full {{ width: 100%; }}
    .error {{ color:#ff9b9b; margin-top: 12px; min-height: 22px; }}
    .app {{ display:none; min-height:100vh; grid-template-columns: 310px 1fr; }}
    aside {{ border-right:1px solid #1d2638; background:#080b13; padding:28px; position:sticky; top:0; height:100vh; }}
    main {{ padding:32px; }}
    nav a {{ display:block; color:#c8d4ee; text-decoration:none; padding:10px 0; }}
    .hero {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-start; }}
    .badge {{ border:1px solid #1e7f4f; background:#09291c; color:#6ee7a8; padding:8px 12px; border-radius:999px; font-size:13px; }}
    .status-strip {{ display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:14px; margin-top:20px; }}
    .pill, .panel, .tile, .chat-box {{ border:1px solid #1d2638; background:#0b1020; border-radius:18px; padding:18px; }}
    .pill span {{ display:block; color:#91a4c7; font-size:12px; text-transform:uppercase; letter-spacing:.12em; }}
    .pill strong {{ display:block; margin-top:6px; }}
    .board-layout {{ display:grid; grid-template-columns: minmax(0, 1.05fr) minmax(360px, .95fr); gap:18px; margin-top: 18px; }}
    .tile-grid {{ display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:14px; }}
    .tile strong {{ display:block; font-size:16px; }}
    .tile span {{ color:#6ee7a8; font-size:13px; display:block; margin:6px 0; }}
    code {{ display:inline-block; background:#070a12; border:1px solid #1d2638; padding:4px 7px; border-radius:8px; color:#9cc9ff; font-size:12px; }}
    pre {{ white-space: pre-wrap; background:#070a12; border:1px solid #1d2638; border-radius:14px; padding:16px; color:#c8d4ee; max-height:520px; overflow:auto; }}
    .roles {{ display:flex; flex-wrap:wrap; gap:8px; margin: 12px 0; }}
    .role {{ border:1px solid #26344d; background:#10182b; color:#dbe7ff; border-radius:999px; padding:7px 10px; font-size:12px; }}
    ul {{ margin: 0; padding-left: 20px; color:#c8d4ee; }}
    .hidden {{ display:none !important; }}
    @media (max-width: 1000px) {{ .app {{ grid-template-columns:1fr; }} aside {{ position:static; height:auto; border-right:0; border-bottom:1px solid #1d2638; }} .status-strip, .board-layout, .tile-grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <section id='loginScreen' class='login-screen'>
    <div class='login-card'>
      <div class='brand'>AI Software Factory</div>
      <h1>Platform Admin Login</h1>
      <p>Sign in to enter Mission Control and start the Board Room meeting.</p>
      <label>Founder email</label>
      <input id='email' value='founder@ai-software-factory.local' autocomplete='username' />
      <label>Password</label>
      <input id='password' type='password' placeholder='FOUNDER_PASSWORD' autocomplete='current-password' />
      <button class='full' onclick='login()'>Enter Mission Control</button>
      <div id='loginError' class='error'></div>
      <p class='muted'>Auth status: {escape(auth['status'])}. Set FOUNDER_PASSWORD and MISSION_CONTROL_SESSION_SECRET in Cloud Run Secret Manager.</p>
    </div>
  </section>

  <section id='app' class='app'>
    <aside>
      <div class='brand'>Platform Admin</div>
      <h1>Mission Control</h1>
      <p class='muted'>Board Room first. Consolidation and cleanup start here.</p>
      <nav>
        <a href='#board'>Board Room</a>
        <a href='#dashboard'>Dashboard</a>
        <a href='/docs'>Swagger fallback</a>
      </nav>
      <button class='secondary' onclick='logout()'>Logout</button>
    </aside>
    <main>
      <div class='hero'>
        <div>
          <div class='brand'>{escape(mc.environment)} · {escape(mc.region)}</div>
          <h1>Board Room Meeting</h1>
          <p class='muted'>{escape(operating['handover_status'])}</p>
        </div>
        <div class='badge'>● {escape(board_room['status'])}</div>
      </div>

      <div class='status-strip'>
        <div class='pill'><span>AI Runtime</span><strong>{escape(ai_status)}</strong></div>
        <div class='pill'><span>Admin Login</span><strong>{escape(auth['status'])}</strong></div>
        <div class='pill'><span>GitHub</span><strong>{escape(str(github.get('status')))}</strong></div>
        <div class='pill'><span>CI Repair</span><strong>{escape(str(ci.get('status')))}</strong></div>
      </div>

      <h2 id='board'>Board Room</h2>
      <section class='panel'>
        <strong>Participants</strong>
        <div class='roles'>{roles}</div>
        <strong>Default agenda</strong>
        <ul>{agenda}</ul>
      </section>

      <section class='board-layout'>
        <div class='chat-box'>
          <label>Founder message to Board Room</label>
          <textarea id='message' placeholder='Example: Audit what we already built and recommend how to consolidate without rebuilding duplicate modules.'></textarea>
          <button onclick='boardRoomChat()'>Start Board Room Discussion</button>
          <button class='secondary' onclick='createWorkflow()'>Create Proposal From Discussion</button>
        </div>
        <div class='chat-box'>
          <strong>Board Room Response</strong>
          <pre id='result'>Login complete. Type your board-room topic and start the meeting.</pre>
        </div>
      </section>

      <h2 id='dashboard'>Dashboard</h2>
      <section class='tile-grid'>{tiles}</section>
      <div class='status-strip'>
        <div class='pill'><span>Founder Console</span><strong>{escape(str(console.get('status')))}</strong></div>
        <div class='pill'><span>Pull Requests</span><strong>{escape(str(prs.get('status')))}</strong></div>
        <div class='pill'><span>Executor Mode</span><strong>{escape(str(github.get('mode')))}</strong></div>
        <div class='pill'><span>Operating Console</span><strong>{escape(operating['status'])}</strong></div>
      </div>
    </main>
  </section>

<script>
let token = localStorage.getItem('mission_control_token') || '';
const loginScreen = document.getElementById('loginScreen');
const app = document.getElementById('app');
const result = document.getElementById('result');
const loginError = document.getElementById('loginError');
function show(data) {{ result.textContent = JSON.stringify(data, null, 2); }}
function showApp() {{ loginScreen.style.display='none'; app.style.display='grid'; }}
function showLogin() {{ loginScreen.style.display='grid'; app.style.display='none'; }}
async function post(url, body) {{
  const response = await fetch(url, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(body) }});
  return await response.json();
}}
async function login() {{
  loginError.textContent = '';
  const data = await post('/mission-control/auth/login', {{ email: document.getElementById('email').value, password: document.getElementById('password').value }});
  if (data.session && data.session.token) {{ token = data.session.token; localStorage.setItem('mission_control_token', token); showApp(); show({{status:'entered-mission-control', user:data.user}}); }}
  else {{ loginError.textContent = data.status || 'Login failed'; }}
}}
async function validateSession() {{
  if (!token) {{ showLogin(); return; }}
  const data = await post('/mission-control/auth/session', {{ token }});
  if (data.authenticated) {{ showApp(); }} else {{ localStorage.removeItem('mission_control_token'); token=''; showLogin(); }}
}}
function logout() {{ token=''; localStorage.removeItem('mission_control_token'); showLogin(); }}
async function boardRoomChat() {{
  const data = await post('/mission-control/board-room/chat', {{ token, message: document.getElementById('message').value }});
  show(data);
}}
async function createWorkflow() {{
  const data = await post('/mission-control/operating-console/workflow', {{ token, action:'create-proposal', message: document.getElementById('message').value }});
  show(data);
}}
validateSession();
</script>
</body>
</html>
"""
