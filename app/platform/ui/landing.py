from __future__ import annotations

from html import escape

from app.platform.auth.service import build_auth_summary
from app.platform.founder_console.service import build_founder_console_summary


def render_public_landing() -> str:
    console = build_founder_console_summary()
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"
    return _page(show_login=False, ai_status=ai_status)


def render_login_page() -> str:
    console = build_founder_console_summary()
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"
    return _page(show_login=True, ai_status=ai_status)


def _page(*, show_login: bool, ai_status: str) -> str:
    auth = build_auth_summary()
    login_class = "modal-backdrop open" if show_login else "modal-backdrop"
    return f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>AI Software Factory</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; min-height:100vh; background: radial-gradient(circle at 50% 45%, #ffffff 0, #fbf6f0 42%, #f5eee6 100%); color:#2e3138; }}
    header {{ height:76px; display:flex; align-items:center; justify-content:space-between; padding:0 8vw; }}
    .logo {{ display:flex; align-items:center; gap:12px; font-weight:800; font-size:25px; }}
    .mark {{ width:27px; height:27px; border-radius:8px; background:linear-gradient(135deg,#2563eb,#ff6b3d); box-shadow:12px 0 0 #ff6b3d, 0 12px 0 #2563eb; transform:scale(.62); }}
    nav {{ display:flex; gap:26px; align-items:center; color:#5e6470; font-size:14px; }}
    nav a {{ color:#5e6470; text-decoration:none; }}
    .actions {{ display:flex; gap:14px; align-items:center; }}
    button, .button {{ border:0; border-radius:13px; padding:11px 18px; font-weight:700; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; }}
    .ghost {{ background:transparent; color:#444b57; }}
    .outline {{ border:1px solid #ff795d; color:#e65235; background:#fff7f2; }}
    .primary {{ background:#2f6df6; color:white; box-shadow:0 10px 28px rgba(47,109,246,.22); }}
    main {{ min-height:calc(100vh - 76px); display:grid; place-items:center; padding:56px 24px 120px; }}
    .hero {{ width:min(820px,100%); text-align:center; }}
    .eyebrow {{ display:inline-flex; gap:8px; align-items:center; border:1px solid #eadfd3; background:rgba(255,255,255,.74); border-radius:999px; padding:8px 13px; color:#6d7280; font-size:13px; }}
    h1 {{ font-size:clamp(44px,7vw,76px); line-height:.98; letter-spacing:-.065em; margin:28px 0 16px; }}
    .sub {{ font-size:17px; color:#636978; margin:0 0 30px; }}
    .prompt {{ margin:0 auto; width:min(720px,100%); border:1px solid #e1d8cf; background:rgba(255,255,255,.88); border-radius:22px; box-shadow:0 20px 70px rgba(78,60,42,.11); padding:18px; display:grid; gap:14px; text-align:left; }}
    .prompt textarea {{ width:100%; min-height:84px; border:0; outline:0; resize:none; background:transparent; font:inherit; font-size:17px; color:#333842; }}
    .prompt-footer {{ display:flex; justify-content:space-between; align-items:center; gap:12px; }}
    .chips {{ display:flex; flex-wrap:wrap; gap:9px; justify-content:center; margin-top:28px; }}
    .chip {{ border:1px solid #e3d9cf; background:rgba(255,255,255,.74); border-radius:10px; padding:10px 13px; color:#3f4652; font-size:14px; }}
    .logos {{ position:fixed; bottom:28px; left:0; right:0; display:flex; justify-content:space-around; gap:30px; color:#b4b1b0; font-weight:800; font-size:28px; opacity:.72; pointer-events:none; }}
    .modal-backdrop {{ display:none; position:fixed; inset:0; background:rgba(245,238,230,.68); backdrop-filter:blur(5px); place-items:center; padding:24px; }}
    .modal-backdrop.open {{ display:grid; }}
    .modal {{ width:min(510px,100%); background:#fffaf6; border:1px solid #e4d9ce; border-radius:20px; box-shadow:0 24px 90px rgba(42,35,28,.2); padding:28px; position:relative; }}
    .close {{ position:absolute; right:18px; top:14px; border:0; background:transparent; font-size:22px; color:#7b746e; cursor:pointer; }}
    .modal h2 {{ text-align:center; font-size:28px; margin:18px 0 18px; }}
    label {{ display:block; margin:12px 0 6px; color:#696f7d; font-size:13px; }}
    input {{ width:100%; border:1px solid #e1d8cf; background:white; border-radius:12px; padding:13px 14px; font:inherit; }}
    .login-error {{ min-height:22px; margin-top:12px; color:#d54535; font-size:13px; }}
    .fineprint {{ border-top:1px solid #e9ddd1; margin-top:20px; padding-top:16px; font-size:12px; color:#7b808d; line-height:1.45; }}
    @media (max-width:850px) {{ header {{ padding:0 22px; }} nav {{ display:none; }} .actions .outline {{ display:none; }} .logos {{ display:none; }} }}
  </style>
</head>
<body>
  <header>
    <div class='logo'><span class='mark'></span><span>AI Software Factory</span></div>
    <nav><a href='#'>Products</a><a href='#'>For Founders</a><a href='#'>Resources</a><a href='#'>Security</a><a href='/docs'>API</a></nav>
    <div class='actions'><button class='ghost' onclick='openLogin()'>Log in</button><button class='outline' onclick='openLogin()'>Enter Mission Control</button></div>
  </header>
  <main>
    <section class='hero'>
      <div class='eyebrow'>● GCP Mission Control · {escape(ai_status)}</div>
      <h1>What will your AI company build?</h1>
      <p class='sub'>Turn founder intent into board-room decisions, approved missions, GitHub pull requests, CI repair, and deployment.</p>
      <div class='prompt'>
        <textarea id='landingPrompt' placeholder='Ask the Board Room: audit the repository, build a feature, review the roadmap...'></textarea>
        <div class='prompt-footer'><span class='sub'>Board Room starts after login</span><button class='primary' onclick='startFromPrompt()'>→</button></div>
      </div>
      <div class='chips'><span class='chip'>Repository audit</span><span class='chip'>Mission proposal</span><span class='chip'>Founder approval</span><span class='chip'>GitHub execution</span></div>
    </section>
  </main>
  <div class='logos'><span>GCP</span><span>GitHub</span><span>OpenAI</span><span>Cloud Run</span><span>Secret Manager</span></div>
  <section id='loginModal' class='{login_class}'>
    <div class='modal'>
      <button class='close' onclick='closeLogin()'>×</button>
      <div class='logo' style='justify-content:center'><span class='mark'></span></div>
      <h2>Log in to Mission Control</h2>
      <label>Founder email</label><input id='email' value='founder@ai-software-factory.local' autocomplete='username' />
      <label>Password</label><input id='password' type='password' placeholder='FOUNDER_PASSWORD' autocomplete='current-password' />
      <button class='primary' style='width:100%; margin-top:16px' onclick='login()'>Continue</button>
      <div id='loginError' class='login-error'></div>
      <div class='fineprint'>Auth status: {escape(auth['status'])}. Set FOUNDER_PASSWORD and MISSION_CONTROL_SESSION_SECRET in Cloud Run Secret Manager.</div>
    </div>
  </section>
<script>
function openLogin() {{ document.getElementById('loginModal').classList.add('open'); }}
function closeLogin() {{ document.getElementById('loginModal').classList.remove('open'); }}
function startFromPrompt() {{ const prompt = document.getElementById('landingPrompt').value || ''; localStorage.setItem('mission_control_draft_prompt', prompt); openLogin(); }}
async function login() {{
  const error = document.getElementById('loginError'); error.textContent = '';
  const response = await fetch('/mission-control/auth/login', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{ email:document.getElementById('email').value, password:document.getElementById('password').value }}) }});
  const data = await response.json();
  if (data.session && data.session.token) {{ localStorage.setItem('mission_control_token', data.session.token); window.location.href = '/mission-control/ui'; }}
  else {{ error.textContent = data.status || 'Login failed'; }}
}}
</script>
</body>
</html>
"""
