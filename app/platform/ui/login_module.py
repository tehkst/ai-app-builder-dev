from __future__ import annotations


def render_login_screen() -> str:
    return """<section id="loginScreen" class="login-screen"><div class="login-card"><div class="brand-small">AI Software Factory</div><div id="signinView"><h1>Platform Admin Login</h1><p class="muted">Sign in to enter Mission Control.</p><label>Founder email</label><input id="email" value="__FOUNDER_EMAIL__" autocomplete="username"><label>Password</label><input id="password" type="password" placeholder="FOUNDER_PASSWORD" autocomplete="current-password"><p style="text-align:right;margin-top:-8px"><a id="forgotLink" style="cursor:pointer;color:#93c5fd;font-size:12px">Forgot password?</a></p><button id="loginBtn" type="button">Enter Mission Control</button><div id="loginError" class="error"></div><p class="muted">Auth status: __AUTH_STATUS__</p><p id="scriptStatus" class="small">Script loading...</p></div><div id="forgotView" style="display:none"><h1>Reset password</h1><p class="muted">Enter the platform admin email and we'll send a reset link.</p><label>Email</label><input id="forgotEmail" value="__FOUNDER_EMAIL__" autocomplete="username"><button id="forgotBtn" type="button">Send reset link</button><div id="forgotMessage" class="muted"></div><p><a id="backToSigninLink" style="cursor:pointer;color:#93c5fd">Back to sign in</a></p></div></div></section>"""


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
function showForgot(){byId('signinView').style.display='none';byId('forgotView').style.display='block';byId('forgotMessage').textContent=''}
function showSignin(){byId('forgotView').style.display='none';byId('signinView').style.display='block'}
async function submitForgot(){var msg=byId('forgotMessage');msg.textContent='Sending...';try{var data=await post('/mission-control/auth/forgot-password',{email:byId('forgotEmail').value});msg.textContent=data.message||'If that email exists, a reset link has been sent.'}catch(e){msg.textContent='Request failed: '+e}}
function bindLoginModule(){var ss=byId('scriptStatus');if(ss){ss.textContent='Script ready'};on('loginBtn','click',login);on('password','keydown',function(e){if(e.key==='Enter'){login()}});on('logoutBtn','click',function(){token='';localStorage.removeItem('mission_control_token');showLogin()});on('forgotLink','click',showForgot);on('backToSigninLink','click',showSignin);on('forgotBtn','click',submitForgot);verifySession()}
"""
