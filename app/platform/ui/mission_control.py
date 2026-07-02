from __future__ import annotations

import os
from html import escape


def render_dashboard() -> str:
    founder_email = escape(os.getenv("FOUNDER_EMAIL", "founder@ai-software-factory.local"))
    return f"""
<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>AI Software Factory · Mission Control</title>
<style>
:root {{ font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; min-height: 100vh; background: radial-gradient(circle at top left, #12305f, #050b14 45%, #020617); color: #f4f8ff; }}
.login {{ min-height: 100vh; display: grid; place-items: center; padding: 28px; }}
.card {{ width: min(480px, 100%); border: 1px solid #24324a; background: linear-gradient(180deg, rgba(17,31,52,.94), rgba(7,13,25,.9)); border-radius: 22px; padding: 30px; box-shadow: 0 24px 80px rgba(0,0,0,.25); }}
.brand {{ color: #9aa8bd; font-size: 12px; letter-spacing: .18em; text-transform: uppercase; }}
h1 {{ margin: 12px 0 8px; font-size: 32px; }}
p {{ color: #9aa8bd; }}
label {{ display: block; margin: 14px 0 6px; color: #9aa8bd; font-size: 13px; }}
input {{ width: 100%; border: 1px solid #24324a; background: #07101e; color: #f4f8ff; border-radius: 12px; padding: 13px; outline: 0; }}
button {{ width: 100%; margin-top: 14px; border: 0; border-radius: 12px; padding: 13px 16px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; font-weight: 800; cursor: pointer; }}
.error {{ color: #ff9b9b; min-height: 22px; margin-top: 12px; }}
.app {{ display: none; min-height: 100vh; padding: 24px; }}
.shell {{ max-width: 1180px; margin: 0 auto; }}
.top {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 18px; }}
.grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
.panel {{ border: 1px solid #24324a; background: #0b1424; border-radius: 16px; padding: 18px; }}
.panel h2 {{ margin: 0 0 8px; font-size: 18px; }}
.link {{ display: inline-block; margin-top: 10px; color: #93c5fd; }}
.logout {{ width: auto; margin: 0; background: #132238; border: 1px solid #24324a; }}
@media(max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} .top {{ flex-direction: column; align-items: flex-start; }} }}
</style>
</head>
<body>
<section id='loginScreen' class='login'>
  <div class='card'>
    <div class='brand'>AI Software Factory</div>
    <h1>Mission Control Login</h1>
    <p>Safe access shell restored. Sign in to continue.</p>
    <label>Founder email</label>
    <input id='email' value='{founder_email}' autocomplete='username'/>
    <label>Password</label>
    <input id='password' type='password' placeholder='FOUNDER_PASSWORD' autocomplete='current-password'/>
    <button id='loginBtn' type='button'>Enter Mission Control</button>
    <div id='loginError' class='error'></div>
    <p id='scriptStatus'>Script loading...</p>
  </div>
</section>
<section id='app' class='app'>
  <div class='shell'>
    <div class='top'>
      <div><div class='brand'>Production · Asia-Southeast1</div><h1>Mission Control</h1><p>Founder access restored. Board Room repair will be applied separately.</p></div>
      <button class='logout' onclick='logout()'>Logout</button>
    </div>
    <div class='grid'>
      <div class='panel'><h2>Board Room</h2><p>INT-01 backend remains available. Conversational UI is paused until BR-01 repair.</p><a class='link' href='/docs'>Open Swagger fallback</a></div>
      <div class='panel'><h2>Company Intelligence</h2><p>Company Intelligence snapshot endpoint is active.</p><a class='link' href='/mission-control/company-intelligence/snapshot' target='_blank'>Open snapshot</a></div>
      <div class='panel'><h2>Runtime</h2><p>Use API endpoints for testing while UI is stabilized.</p><a class='link' href='/mission-control/operating-console' target='_blank'>Open operating console</a></div>
    </div>
  </div>
</section>
<script>
(function() {{
  var token = localStorage.getItem('mission_control_token') || '';
  function byId(id) {{ return document.getElementById(id); }}
  function showLogin() {{ byId('loginScreen').style.display = 'grid'; byId('app').style.display = 'none'; }}
  function showApp() {{ byId('loginScreen').style.display = 'none'; byId('app').style.display = 'block'; }}
  function post(url, body) {{ return fetch(url, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(body) }}).then(function(r) {{ return r.json(); }}); }}
  window.logout = function() {{ token = ''; localStorage.removeItem('mission_control_token'); showLogin(); }};
  window.login = async function() {{
    var err = byId('loginError');
    var btn = byId('loginBtn');
    err.textContent = '';
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    try {{
      var data = await post('/mission-control/auth/login', {{ email: byId('email').value, password: byId('password').value }});
      if (data.session && data.session.token) {{
        token = data.session.token;
        localStorage.setItem('mission_control_token', token);
        showApp();
      }} else {{
        err.textContent = data.status || data.error || 'Login failed';
      }}
    }} catch (e) {{ err.textContent = 'Login failed: ' + e; }}
    finally {{ btn.disabled = false; btn.textContent = 'Enter Mission Control'; }}
  }};
  document.addEventListener('DOMContentLoaded', async function() {{
    byId('scriptStatus').textContent = 'Script ready';
    byId('loginBtn').addEventListener('click', window.login);
    if (!token) {{ showLogin(); return; }}
    try {{
      var session = await post('/mission-control/auth/session', {{ token: token }});
      if (session.authenticated) showApp(); else showLogin();
    }} catch (e) {{ showLogin(); }}
  }});
}})();
</script>
</body>
</html>
"""
