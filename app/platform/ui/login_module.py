from __future__ import annotations


def render_login_screen() -> str:
    return """<section id="loginScreen" class="login-screen"><div class="login-card"><div class="brand-small">AI Software Factory</div><h1>Platform Admin Login</h1><p class="muted">Sign in to enter Mission Control.</p><label>Founder email</label><input id="email" value="__FOUNDER_EMAIL__" autocomplete="username"><label>Password</label><input id="password" type="password" placeholder="FOUNDER_PASSWORD" autocomplete="current-password"><button id="loginBtn" type="button">Enter Mission Control</button><div id="loginError" class="error"></div><p class="muted">Auth status: __AUTH_STATUS__</p><p id="scriptStatus" class="small">Script loading...</p></div></section>"""


def render_login_script() -> str:
    return """
var token=localStorage.getItem('mission_control_token')||'';
function byId(id){return document.getElementById(id)}
function on(id,event,handler){var el=byId(id);if(el){el.addEventListener(event,handler)}}
function showApp(){byId('loginScreen').style.display='none';byId('app').style.display='grid'}
function showLogin(){byId('loginScreen').style.display='grid';byId('app').style.display='none'}
function post(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()})}
async function login(){var err=byId('loginError');var btn=byId('loginBtn');err.textContent='';btn.disabled=true;btn.textContent='Signing in...';try{var data=await post('/mission-control/auth/login',{email:byId('email').value,password:byId('password').value});if(data.session&&data.session.token){token=data.session.token;localStorage.setItem('mission_control_token',token);showApp()}else{err.textContent=data.status||data.error||'Login failed'}}catch(e){err.textContent='Login request failed: '+e}finally{btn.disabled=false;btn.textContent='Enter Mission Control'}}
async function verifySession(){if(!token){showLogin();return}try{var data=await post('/mission-control/auth/session',{token:token});if(data.authenticated){showApp()}else{showLogin()}}catch(e){showLogin()}}
function bindLoginModule(){var ss=byId('scriptStatus');if(ss){ss.textContent='Script ready'};on('loginBtn','click',login);on('password','keydown',function(e){if(e.key==='Enter'){login()}});on('logoutBtn','click',function(){token='';localStorage.removeItem('mission_control_token');showLogin()});verifySession()}
"""
