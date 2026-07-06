from __future__ import annotations

import os
from html import escape

from app.platform.auth.service import build_auth_summary
from app.platform.founder_console.service import build_founder_console_summary
from app.platform.mission_control.service import build_mission_control_summary


def render_stable_founder_dashboard() -> str:
    mc = build_mission_control_summary()
    console = build_founder_console_summary()
    auth = build_auth_summary()
    founder_email = escape(os.getenv("FOUNDER_EMAIL", "founder@ai-software-factory.local"))
    ai_status = escape(f"{console['runtime']['ai_provider']} · {console['runtime']['model']}")
    env = escape(str(getattr(mc, "environment", "production")))
    region = escape(str(getattr(mc, "region", "asia-southeast1")))
    auth_status = escape(str(auth.get("status", "unknown")))
    return HTML.replace("__FOUNDER_EMAIL__", founder_email).replace("__ENV__", env).replace("__REGION__", region).replace("__AI_STATUS__", ai_status).replace("__AUTH_STATUS__", auth_status)


HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Software Factory Mission Control</title>
<style>
:root{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:dark;--line:#22314d;--text:#f2f7ff;--muted:#9aa9c2;--blue:#3b82f6;--purple:#8b5cf6;--green:#22c55e}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 20% 0,#122a55 0,#07111f 38%,#030712 100%);color:var(--text)}button,input,textarea{font:inherit}.login-screen{min-height:100vh;display:grid;place-items:center;padding:28px}.login-card{width:min(480px,100%);border:1px solid var(--line);background:#08111f;border-radius:26px;padding:30px;box-shadow:0 30px 90px rgba(0,0,0,.4)}.brand-small{font-size:12px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase}.muted,.small{color:var(--muted)}label{display:block;color:var(--muted);font-size:13px;margin:14px 0 6px}input,textarea{width:100%;border:1px solid var(--line);background:#07101e;color:var(--text);border-radius:13px;padding:13px;outline:0}.primary,.login-card button{border:0;border-radius:13px;padding:13px 17px;background:linear-gradient(135deg,var(--blue),var(--purple));color:white;font-weight:800}.login-card button{width:100%;margin-top:14px}.error{color:#ff9b9b;margin-top:12px;min-height:22px}.app{display:none;min-height:100vh;grid-template-columns:280px 1fr}aside{height:100vh;padding:20px 16px;border-right:1px solid var(--line);background:#040c18}.logo{display:flex;gap:12px;align-items:center;margin-bottom:20px}.mark{width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#6366f1,#60a5fa);display:grid;place-items:center;font-weight:900}.logo strong{display:block;font-size:18px}.logo span{color:#60a5fa;font-size:12px;text-transform:uppercase;letter-spacing:.08em}.nav button{width:100%;text-align:left;border:0;background:transparent;color:#c7d2e7;padding:11px 12px;border-radius:10px;margin:3px 0}.nav button.active,.nav button:hover{background:linear-gradient(90deg,#1e40af,#6d28d9);color:white}main{padding:24px}.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.card{border:1px solid var(--line);background:linear-gradient(180deg,rgba(15,27,49,.88),rgba(8,15,29,.82));border-radius:16px;padding:18px;margin-bottom:14px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.kpi{font-size:28px;font-weight:900}.good{color:var(--green);font-weight:800}.secondary{border:1px solid var(--line);background:#13233d;color:#dbeafe;border-radius:10px;padding:10px 13px;font-weight:800}.logout{border:1px solid var(--line);background:#13233d;color:#dbeafe;border-radius:10px;padding:10px 13px;font-weight:800}pre{white-space:pre-wrap;background:#050b15;border:1px solid var(--line);border-radius:12px;padding:14px;color:#dbeafe}.section{display:none}.section.active{display:block}@media(max-width:900px){.app{grid-template-columns:1fr}aside{height:auto}.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<section id="loginScreen" class="login-screen">
  <div class="login-card">
    <div class="brand-small">AI Software Factory</div>
    <h1>Platform Admin Login</h1>
    <p class="muted">Sign in to enter Mission Control.</p>
    <label>Founder email</label>
    <input id="email" value="__FOUNDER_EMAIL__" autocomplete="username">
    <label>Password</label>
    <input id="password" type="password" placeholder="FOUNDER_PASSWORD" autocomplete="current-password">
    <button id="loginBtn" type="button">Enter Mission Control</button>
    <div id="loginError" class="error"></div>
    <p class="muted">Auth status: __AUTH_STATUS__</p>
    <p id="scriptStatus" class="small">Script loading...</p>
  </div>
</section>
<section id="app" class="app">
  <aside>
    <div class="logo"><div class="mark">AI</div><div><strong>AI Software Factory</strong><span>Mission Control</span></div></div>
    <div class="nav">
      <button class="active" data-section="home">⌂ Home</button>
      <button data-section="board">▣ Board Room</button>
      <button data-section="projects">▤ Projects</button>
      <button data-section="workflows">⌘ Workflows</button>
      <button data-section="executions">▧ Executions</button>
      <button data-section="deployments">◇ Deployments</button>
      <button data-section="settings">⚙ Settings</button>
    </div>
    <p><button class="logout" id="logoutBtn">Logout</button></p>
  </aside>
  <main>
    <div class="topbar"><div><div class="brand-small">__ENV__ · __REGION__</div><h1>Founder Experience</h1></div><button class="primary" id="openBoardBtn">Board Room</button></div>
    <section id="home" class="section active"><div class="card"><h2>Mission Control Restored</h2><p class="muted">Login shell is running in emergency safe mode. Backend runtime remains available.</p><div class="grid"><div class="card"><div>Runtime</div><div class="kpi">__AI_STATUS__</div></div><div class="card"><div>Auth</div><div class="good">__AUTH_STATUS__</div></div><div class="card"><div>Status</div><div class="good">Safe Mode</div></div></div></div></section>
    <section id="board" class="section"><div class="card"><h2>Board Room</h2><textarea id="message" placeholder="Tell the Board Room what you want to discuss."></textarea><p><button class="primary" id="boardBtn">Send</button></p><pre id="result">Ready.</pre></div></section>
    <section id="projects" class="section"><div class="card"><h2>Projects</h2><p class="muted">Project dashboard will be restored after login stability is confirmed.</p></div></section>
    <section id="workflows" class="section"><div class="card"><h2>Workflows</h2><p class="muted">Board → Design → Code → Test → PR → Deploy.</p></div></section>
    <section id="executions" class="section"><div class="card"><h2>Executions</h2><p class="muted">Mission Runtime and repository packages remain available through backend APIs.</p></div></section>
    <section id="deployments" class="section"><div class="card"><h2>Deployments</h2><p class="muted">Cloud Run production service is active.</p></div></section>
    <section id="settings" class="section"><div class="card"><h2>Settings</h2><p>Auth status: __AUTH_STATUS__</p><p>Runtime: __AI_STATUS__</p></div></section>
  </main>
</section>
<script>
(function(){
  var token = localStorage.getItem('mission_control_token') || '';
  function byId(id){ return document.getElementById(id); }
  function showApp(){ byId('loginScreen').style.display='none'; byId('app').style.display='grid'; }
  function showLogin(){ byId('loginScreen').style.display='grid'; byId('app').style.display='none'; }
  function post(url, body){ return fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}).then(function(r){ return r.json(); }); }
  function showResult(data){ var el=byId('result'); if(el){ el.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2); } }
  function showSection(name){
    document.querySelectorAll('.section').forEach(function(s){ s.classList.remove('active'); });
    document.querySelectorAll('.nav button').forEach(function(b){ b.classList.remove('active'); });
    var section = byId(name); if(section){ section.classList.add('active'); }
    var nav = document.querySelector('.nav button[data-section="' + name + '"]'); if(nav){ nav.classList.add('active'); }
  }
  async function login(){
    var err=byId('loginError'); var btn=byId('loginBtn');
    err.textContent=''; btn.disabled=true; btn.textContent='Signing in...';
    try{
      var data = await post('/mission-control/auth/login', {email:byId('email').value, password:byId('password').value});
      if(data.session && data.session.token){ token=data.session.token; localStorage.setItem('mission_control_token', token); showApp(); }
      else{ err.textContent = data.status || data.error || 'Login failed'; }
    }catch(e){ err.textContent = 'Login request failed: ' + e; }
    finally{ btn.disabled=false; btn.textContent='Enter Mission Control'; }
  }
  async function verifySession(){
    if(!token){ showLogin(); return; }
    try{ var data = await post('/mission-control/auth/session', {token:token}); if(data.authenticated){ showApp(); } else { showLogin(); } }
    catch(e){ showLogin(); }
  }
  document.addEventListener('DOMContentLoaded', function(){
    byId('scriptStatus').textContent='Script ready';
    byId('loginBtn').addEventListener('click', login);
    byId('password').addEventListener('keydown', function(e){ if(e.key === 'Enter'){ login(); } });
    byId('logoutBtn').addEventListener('click', function(){ token=''; localStorage.removeItem('mission_control_token'); showLogin(); });
    byId('openBoardBtn').addEventListener('click', function(){ showSection('board'); });
    document.querySelectorAll('.nav button[data-section]').forEach(function(b){ b.addEventListener('click', function(){ showSection(this.dataset.section); }); });
    byId('boardBtn').addEventListener('click', async function(){
      showResult('Board Room is thinking...');
      try{ showResult(await post('/mission-control/operating-console/chat', {token:token, message:byId('message').value})); }
      catch(e){ showResult('Board Room request failed: ' + e); }
    });
    verifySession();
  });
})();
</script>
</body>
</html>
"""
