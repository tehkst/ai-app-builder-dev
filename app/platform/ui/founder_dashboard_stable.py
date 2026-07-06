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
:root{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:dark;--line:#22314d;--text:#f2f7ff;--muted:#9aa9c2;--blue:#3b82f6;--purple:#8b5cf6;--green:#22c55e;--orange:#f97316;--panel:#0b1426}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 20% 0,#122a55 0,#07111f 38%,#030712 100%);color:var(--text)}button,input,textarea{font:inherit}button{cursor:pointer}.login-screen{min-height:100vh;display:grid;place-items:center;padding:28px}.login-card{width:min(480px,100%);border:1px solid var(--line);background:#08111f;border-radius:26px;padding:30px;box-shadow:0 30px 90px rgba(0,0,0,.4)}.brand-small{font-size:12px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase}.muted,.small{color:var(--muted)}label{display:block;color:var(--muted);font-size:13px;margin:14px 0 6px}input,textarea{width:100%;border:1px solid var(--line);background:#07101e;color:var(--text);border-radius:13px;padding:13px;outline:0}.primary,.login-card button{border:0;border-radius:13px;padding:13px 17px;background:linear-gradient(135deg,var(--blue),var(--purple));color:white;font-weight:800}.login-card button{width:100%;margin-top:14px}.error{color:#ff9b9b;margin-top:12px;min-height:22px}.app{display:none;min-height:100vh;grid-template-columns:280px 1fr}aside{height:100vh;padding:20px 16px;border-right:1px solid var(--line);background:#040c18;position:sticky;top:0}.logo{display:flex;gap:12px;align-items:center;margin-bottom:20px}.mark{width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#6366f1,#60a5fa);display:grid;place-items:center;font-weight:900}.logo strong{display:block;font-size:18px}.logo span{color:#60a5fa;font-size:12px;text-transform:uppercase;letter-spacing:.08em}.nav button{width:100%;text-align:left;border:0;background:transparent;color:#c7d2e7;padding:11px 12px;border-radius:10px;margin:3px 0}.nav button.active,.nav button:hover{background:linear-gradient(90deg,#1e40af,#6d28d9);color:white}main{padding:24px}.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;gap:14px}.card{border:1px solid var(--line);background:linear-gradient(180deg,rgba(15,27,49,.88),rgba(8,15,29,.82));border-radius:16px;padding:18px;margin-bottom:14px}.hero{padding:22px}.hero h2{font-size:28px;margin:0 0 6px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:14px}.kpi{font-size:28px;font-weight:900}.good{color:var(--green);font-weight:800}.warn{color:#fbbf24;font-weight:800}.secondary{border:1px solid var(--line);background:#13233d;color:#dbeafe;border-radius:10px;padding:10px 13px;font-weight:800}.logout{border:1px solid var(--line);background:#13233d;color:#dbeafe;border-radius:10px;padding:10px 13px;font-weight:800}pre{white-space:pre-wrap;background:#050b15;border:1px solid var(--line);border-radius:12px;padding:14px;color:#dbeafe}.section{display:none}.section.active{display:block}.row{display:flex;justify-content:space-between;gap:12px;border-top:1px solid rgba(255,255,255,.07);padding:12px 0}.tag{display:inline-flex;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:800;background:#12315e;color:#93c5fd}.pipeline{display:flex;align-items:center;justify-content:space-between;gap:8px;overflow:auto}.stage{text-align:center;min-width:92px}.stage-icon{width:46px;height:46px;border-radius:14px;background:#102846;border:1px solid #24405f;display:grid;place-items:center;margin:0 auto 8px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}@media(max-width:1000px){.app{grid-template-columns:1fr}aside{height:auto;position:relative}.grid,.grid4,.layout{grid-template-columns:1fr}}
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
    <section id="home" class="section active">
      <div class="card hero"><h2>Good evening, Toni 👋</h2><p class="muted">Mission Control is restored with a safe dashboard shell. What do you want the company to build, fix, review, or deploy?</p><div class="actions"><button class="secondary" data-jump="board">Open Board Room</button><button class="secondary" data-jump="workflows">Review Workflow</button><button class="secondary" data-jump="executions">Execution Status</button></div></div>
      <div class="grid4"><div class="card"><div class="small">Runtime</div><div class="kpi">__AI_STATUS__</div></div><div class="card"><div class="small">Auth</div><div class="good">__AUTH_STATUS__</div></div><div class="card"><div class="small">Mode</div><div class="kpi">Stable</div></div><div class="card"><div class="small">Governance</div><div class="good">Founder gated</div></div></div>
      <div class="layout"><div class="card"><h2>Active Projects</h2><div class="row"><span>AI Software Factory</span><span class="tag">Mission Control</span></div><div class="row"><span>Repository Execution Runtime</span><span class="tag">Ready</span></div><div class="row"><span>Founder Dashboard</span><span class="tag">Restoring</span></div></div><div class="card"><h2>Company Activity</h2><div class="row"><span>Login restored</span><span class="good">Live</span></div><div class="row"><span>Dashboard shell</span><span class="good">Safe</span></div><div class="row"><span>Advanced UI</span><span class="warn">Incremental</span></div></div></div>
    </section>
    <section id="board" class="section"><div class="card"><h2>Board Room</h2><p class="muted">Executive discussion workspace. This uses the existing backend endpoint and keeps the login script unchanged.</p><textarea id="message" placeholder="Tell the Board Room what you want to discuss."></textarea><p><button class="primary" id="boardBtn">Send</button></p><pre id="result">Ready.</pre></div></section>
    <section id="projects" class="section"><div class="grid"><div class="card"><h2>AI Software Factory</h2><p class="muted">Main autonomous engineering platform.</p><span class="tag">Active</span></div><div class="card"><h2>Mission Runtime</h2><p class="muted">Planning, repository package, PR package, release package, and loop package.</p><span class="tag">Live</span></div><div class="card"><h2>Dashboard</h2><p class="muted">Safe shell restored. Full UI will return section by section.</p><span class="tag">MC-UI-02</span></div></div></section>
    <section id="workflows" class="section"><div class="card"><h2>Workflow Pipeline</h2><div class="pipeline"><div class="stage"><div class="stage-icon">♙</div><strong>Board</strong></div><span>→</span><div class="stage"><div class="stage-icon">▧</div><strong>Design</strong></div><span>→</span><div class="stage"><div class="stage-icon">⌘</div><strong>Code</strong></div><span>→</span><div class="stage"><div class="stage-icon">✓</div><strong>Test</strong></div><span>→</span><div class="stage"><div class="stage-icon">PR</div><strong>Review</strong></div><span>→</span><div class="stage"><div class="stage-icon">◇</div><strong>Deploy</strong></div></div></div></section>
    <section id="executions" class="section"><div class="grid"><div class="card"><h2>Repository Package</h2><p class="good">Available</p></div><div class="card"><h2>PR Package</h2><p class="good">Available</p></div><div class="card"><h2>Release Package</h2><p class="good">Available</p></div></div><div class="card"><h2>Execution Policy</h2><p class="muted">No auto-merge and no auto-deploy. Founder approval remains required.</p></div></section>
    <section id="deployments" class="section"><div class="card"><h2>Deployments</h2><p class="muted">Cloud Run production service is active in __REGION__.</p><div class="row"><span>Current environment</span><span class="tag">__ENV__</span></div><div class="row"><span>Verification</span><span class="good">Manual traffic check required</span></div></div></section>
    <section id="settings" class="section"><div class="grid"><div class="card"><h2>Authentication</h2><p class="good">__AUTH_STATUS__</p></div><div class="card"><h2>Runtime</h2><p>__AI_STATUS__</p></div><div class="card"><h2>Environment</h2><p>__ENV__ · __REGION__</p></div></div></section>
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
    document.querySelectorAll('button[data-jump]').forEach(function(b){ b.addEventListener('click', function(){ showSection(this.dataset.jump); }); });
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
