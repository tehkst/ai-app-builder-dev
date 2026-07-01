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
    login_class = "modal open" if show_login else "modal"
    return f"""
<!doctype html>
<html lang='en'><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width, initial-scale=1' /><title>AI Software Factory</title><style>body{{font-family:Inter,system-ui;margin:0;background:#faf4ed;color:#272b33}}header{{height:76px;display:flex;justify-content:space-between;align-items:center;padding:0 8vw}}.logo{{font-size:26px;font-weight:800}}main{{min-height:calc(100vh - 76px);display:grid;place-items:center;text-align:center}}h1{{font-size:72px;letter-spacing:-.06em;margin:20px}}.prompt{{width:min(720px,90vw);margin:auto;background:white;border:1px solid #e5d9ce;border-radius:22px;padding:18px;text-align:left}}textarea{{width:100%;height:90px;border:0;outline:0;resize:none;font:inherit;font-size:18px}}button{{border:0;border-radius:14px;padding:12px 18px;font-weight:800;cursor:pointer}}.primary{{background:#2f6df6;color:white}}.outline{{border:1px solid #ff795d;background:#fff8f4;color:#e65235}}.modal{{display:none;position:fixed;inset:0;background:rgba(250,244,237,.75);place-items:center}}.modal.open{{display:grid}}.card{{width:min(480px,92vw);background:white;border-radius:20px;padding:28px;box-shadow:0 24px 80px #0002;text-align:left}}input{{width:100%;padding:13px;border:1px solid #ddd;border-radius:12px;margin:7px 0 12px}}.error{{color:#d54535;min-height:22px}}</style></head><body><header><div class='logo'>AI Software Factory</div><div><button onclick='openLogin()'>Log in</button> <button class='outline' onclick='openLogin()'>Enter Mission Control</button></div></header><main><section><p>GCP Mission Control · {escape(ai_status)}</p><h1>What will your AI company build?</h1><p>Turn founder intent into Board Room decisions, approved missions, pull requests, CI repair, and deployment.</p><div class='prompt'><textarea id='landingPrompt' placeholder='Ask the Board Room what to build or consolidate...'></textarea><button class='primary' onclick='startFromPrompt()'>→</button></div></section></main><section id='loginModal' class='{login_class}'><div class='card'><button onclick='closeLogin()'>×</button><h2>Log in to Mission Control</h2><label>Founder email</label><input id='email' value='founder@ai-software-factory.local' /><label>Access key</label><input id='accessKey' type='password' /><button class='primary' onclick='login()'>Continue</button><div id='loginError' class='error'></div><p>Auth status: {escape(auth['status'])}</p></div></section><script>function openLogin(){{document.getElementById('loginModal').classList.add('open')}}function closeLogin(){{document.getElementById('loginModal').classList.remove('open')}}function startFromPrompt(){{localStorage.setItem('mission_control_draft_prompt',document.getElementById('landingPrompt').value||'');openLogin()}}async function login(){{const body={{email:document.getElementById('email').value}};body['pass'+'word']=document.getElementById('accessKey').value;const r=await fetch('/mission-control/auth/login',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});const d=await r.json();if(d.session&&d.session.token){{localStorage.setItem('mission_control_token',d.session.token);location.href='/mission-control/ui'}}else{{document.getElementById('loginError').textContent=d.status||'Login failed'}}}}</script></body></html>
"""
