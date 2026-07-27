from __future__ import annotations

from html import escape

from app.platform.auth.service import build_auth_summary
from app.platform.founder_console.service import build_founder_console_summary


AGENTS = [
    ("AI CEO", "Strategy"),
    ("AI CTO", "Architecture"),
    ("Chief Architect", "Systems"),
    ("Engineering Manager", "Delivery"),
    ("Senior Engineer", "Code"),
    ("QA Lead", "Validation"),
    ("DevOps Lead", "Deployments"),
    ("Security Officer", "Risk"),
    ("Product Manager", "Roadmap"),
    ("Finance Analyst", "Unit economics"),
    ("Legal Advisor", "Governance"),
    ("Data Engineer", "Memory"),
]

SHARED_STYLE = """
    :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #2b2d33; background: #fbf7f2; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: radial-gradient(circle at 50% 20%, #fff 0, #fbf7f2 45%, #f6eee5 100%); }
    a { color: inherit; text-decoration: none; }
    .topbar { height: 78px; display: flex; align-items: center; justify-content: space-between; padding: 0 7vw; }
    .brand { display: flex; align-items: center; gap: 10px; font-weight: 900; font-size: 26px; letter-spacing: -.045em; }
    .mark { width: 29px; height: 29px; border-radius: 9px; background: linear-gradient(135deg, #2b6df6, #6ee7ff); box-shadow: 0 14px 34px rgba(43,109,246,.28); }
    .nav { display: flex; gap: 24px; align-items: center; color: #747782; font-size: 14px; }
    .nav button, .hero button, .login-card button { border: 0; border-radius: 999px; padding: 12px 18px; font-weight: 800; cursor: pointer; }
    .ghost { background: transparent; color: #2b2d33; }
    .outline { background: transparent; border: 1px solid #2b6df6 !important; color: #2b6df6; }
    .primary { background: #2b6df6; color: white; box-shadow: 0 18px 45px rgba(43,109,246,.24); }
    .hero { min-height: 600px; display: grid; place-items: center; text-align: center; padding: 44px 20px 4px; }
    .eyebrow { display: inline-flex; color: #2b6df6; font-weight: 900; font-size: 13px; letter-spacing: .11em; text-transform: uppercase; }
    h1 { font-size: clamp(48px, 7.6vw, 88px); line-height: .94; letter-spacing: -.08em; margin: 24px auto 18px; max-width: 1000px; }
    .subtitle { color: #686b75; font-size: 18px; max-width: 740px; margin: 0 auto 28px; line-height: 1.5; }
    .prompt { width: min(760px, 92vw); margin: 0 auto; background: white; border: 1px solid #e8ded4; border-radius: 24px; padding: 16px; display: grid; grid-template-columns: 1fr auto; gap: 12px; box-shadow: 0 24px 90px rgba(30,26,23,.08); }
    .prompt input { border: 0; outline: none; font: inherit; font-size: 16px; padding: 16px; }
    .chips { display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
    .chip { background: rgba(255,255,255,.8); border: 1px solid #eadfd5; border-radius: 999px; padding: 9px 14px; color: #3a3d46; font-size: 13px; }
    .workforce { padding: 26px 7vw 76px; }
    .section-title { text-align: center; font-size: 13px; color: #8a8d98; margin-bottom: 20px; text-transform: uppercase; letter-spacing: .14em; font-weight: 900; }
    .agents { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 14px; }
    .agent { background: rgba(255,255,255,.82); border: 1px solid #eadfd5; border-radius: 18px; padding: 16px; min-height: 96px; transition: transform .16s ease, box-shadow .16s ease; }
    .agent:hover { transform: translateY(-2px); box-shadow: 0 18px 50px rgba(30,26,23,.08); }
    .agent strong { display: block; font-size: 14px; }
    .agent span { display: block; color: #8a8d98; font-size: 12px; margin-top: 6px; }
    .activity { margin-top: 20px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
    .activity-card { background: #111827; color: #e8eefc; border-radius: 20px; padding: 18px; min-height: 112px; box-shadow: 0 24px 80px rgba(17,24,39,.12); }
    .activity-card span { color: #93a4bf; font-size: 12px; text-transform: uppercase; letter-spacing: .1em; }
    .activity-card strong { display: block; margin-top: 12px; }
    .modal { position: fixed; inset: 0; display: none; place-items: center; background: rgba(28,24,21,.22); backdrop-filter: blur(10px); padding: 24px; z-index: 50; }
    .modal.active { display: grid; }
    .login-card { width: min(470px, 100%); background: #fffaf5; border: 1px solid #e8ded4; border-radius: 22px; padding: 30px; box-shadow: 0 30px 120px rgba(30,26,23,.25); position: relative; }
    .close { position: absolute; right: 16px; top: 12px; background: transparent; color: #747782; font-size: 22px; padding: 8px; }
    .login-card h2 { text-align: center; margin: 12px 0 18px; font-size: 26px; letter-spacing: -.04em; }
    label { display: block; font-size: 13px; color: #686b75; margin: 14px 0 7px; }
    .field { width: 100%; border: 1px solid #eadfd5; background: white; color: #2b2d33; border-radius: 14px; padding: 14px; font: inherit; }
    .full { width: 100%; margin-top: 16px; border-radius: 14px !important; }
    .note, .error { color: #8a8d98; font-size: 13px; line-height: 1.35; margin-top: 14px; }
    .error { color: #cf3d3d; min-height: 18px; }
    .switch-mode { text-align: center; margin-top: 12px; font-size: 13px; color: #747782; }
    .switch-mode a, .forgot-link { color: #2b6df6; font-weight: 800; cursor: pointer; }
    .forgot-row { text-align: right; margin-top: -6px; }
    .forgot-row a { font-size: 12px; }
    @media (max-width: 900px) { .nav a { display: none; } .agents, .activity { grid-template-columns: repeat(2, minmax(0,1fr)); } .prompt { grid-template-columns: 1fr; } }
    @media (max-width: 560px) { .topbar { padding: 0 20px; } .brand { font-size: 20px; } .agents, .activity { grid-template-columns: 1fr; } h1 { font-size: 44px; } }
"""


def render_public_landing() -> str:
    console = build_founder_console_summary()
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"
    return _page(show_login=False, ai_status=ai_status)


def render_login_page() -> str:
    console = build_founder_console_summary()
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"
    return _page(show_login=True, ai_status=ai_status)


def _page(*, show_login: bool, ai_status: str) -> str:
    modal_class = "modal active" if show_login else "modal"
    agent_cards = "".join(
        f"<article class='agent'><strong>{escape(name)}</strong><span>{escape(role)}</span></article>"
        for name, role in AGENTS
    )
    return f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>AI Software Factory</title>
  <style>
{SHARED_STYLE}
  </style>
</head>
<body>
  <header class='topbar'>
    <a class='brand' href='/'><span class='mark'></span><span>AI Software Factory</span></a>
    <nav class='nav'><a>Products</a><a>Platform</a><a>Enterprise</a><a>Pricing</a><button class='ghost' onclick='openLogin()'>Log in</button><button class='outline' onclick='openLogin()'>Sign up</button></nav>
  </header>
  <main>
    <section class='hero'>
      <div>
        <div class='eyebrow'>● Autonomous AI Company</div>
        <h1>Build companies, not just software.</h1>
        <p class='subtitle'>A founder-controlled AI board room, engineering team, GitHub executor, CI repair loop, and Cloud Run workflow in one operating platform.</p>
        <div class='prompt'><input id='landingPrompt' placeholder='What shall we build today?' /><button class='primary' onclick='startFromPrompt()'>Start</button></div>
        <div class='chips'><span class='chip'>Audit our architecture</span><span class='chip'>Build SaaS module</span><span class='chip'>Open a PR</span><span class='chip'>Deploy to Cloud Run</span></div>
      </div>
    </section>
    <section class='workforce'>
      <div class='section-title'>AI Workforce</div><div class='agents'>{agent_cards}</div>
      <div class='activity'><article class='activity-card'><span>Runtime</span><strong>{escape(ai_status)}</strong></article><article class='activity-card'><span>Board Room</span><strong>Founder meeting ready</strong></article><article class='activity-card'><span>GitHub</span><strong>PR workflow connected</strong></article><article class='activity-card'><span>Governance</span><strong>Approval before execution</strong></article></div>
    </section>
  </main>
  <div id='loginModal' class='{modal_class}'>
    <div class='login-card'>
      <button class='close' onclick='closeLogin()'>×</button>
      <div class='brand' style='justify-content:center;font-size:18px'><span class='mark'></span><span>AI Software Factory</span></div>
      <div id='signinView'>
        <h2 id='customerHeading'>Sign in</h2>
        <p style='text-align:center;color:#8a8d98;font-size:13px;margin-top:-6px'>Sign in or create your own workspace.</p>
        <div id='customerNameFields' style='display:none'>
          <label>Full name</label><input class='field' id='customerFullName' autocomplete='name' />
          <label>Organization name</label><input class='field' id='customerOrgName' autocomplete='organization' />
        </div>
        <label>Email</label><input class='field' id='customerEmail' autocomplete='username' />
        <label>Password</label><input class='field' id='customerPassword' type='password' autocomplete='current-password' />
        <div class='forgot-row'><a class='forgot-link' onclick='showForgot()'>Forgot password?</a></div>
        <button class='primary full' id='customerSubmitBtn' onclick='customerSubmit()'>Sign in</button>
        <div id='customerError' class='error'></div>
        <p class='switch-mode' id='customerSwitchMode'>New here? <a onclick='switchCustomerMode()'>Create an account</a></p>
      </div>
      <div id='forgotView' style='display:none'>
        <h2>Reset your password</h2>
        <p style='text-align:center;color:#8a8d98;font-size:13px;margin-top:-6px'>Enter your email and we'll send you a reset link.</p>
        <label>Email</label><input class='field' id='forgotEmail' autocomplete='username' />
        <button class='primary full' onclick='submitForgot()'>Send reset link</button>
        <div id='forgotMessage' class='note'></div>
        <p class='switch-mode'><a onclick='showSignin()'>Back to sign in</a></p>
      </div>
    </div>
  </div>
<script>
var customerMode='login';
function openLogin(){{document.getElementById('loginModal').classList.add('active');}}
function closeLogin(){{document.getElementById('loginModal').classList.remove('active');}}
function startFromPrompt(){{localStorage.setItem('mission_control_draft_prompt',document.getElementById('landingPrompt').value||'');openLogin();}}
function showForgot(){{document.getElementById('signinView').style.display='none';document.getElementById('forgotView').style.display='block';document.getElementById('forgotMessage').textContent='';}}
function showSignin(){{document.getElementById('forgotView').style.display='none';document.getElementById('signinView').style.display='block';}}
function switchCustomerMode(){{customerMode=customerMode==='login'?'signup':'login';document.getElementById('customerHeading').textContent=customerMode==='login'?'Sign in':'Create your workspace';document.getElementById('customerNameFields').style.display=customerMode==='signup'?'block':'none';document.getElementById('customerSubmitBtn').textContent=customerMode==='login'?'Sign in':'Create account';document.getElementById('customerSwitchMode').innerHTML=customerMode==='login'?'New here? <a onclick="switchCustomerMode()">Create an account</a>':'Already have an account? <a onclick="switchCustomerMode()">Sign in</a>';document.getElementById('customerError').textContent='';}}
async function customerSubmit(){{const err=document.getElementById('customerError');err.textContent='';const email=document.getElementById('customerEmail').value;const password=document.getElementById('customerPassword').value;try{{let response;if(customerMode==='signup'){{response=await fetch('/api/auth/register',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:email,full_name:document.getElementById('customerFullName').value,password:password,organization_name:document.getElementById('customerOrgName').value}})}});}}else{{response=await fetch('/api/auth/login',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:email,password:password}})}});}}const data=await response.json();if(response.ok&&data.access_token){{localStorage.setItem('customer_token',data.access_token);window.location.href='/customer/home';}}else{{err.textContent=data.detail||'Request failed';}}}}catch(error){{err.textContent='Request failed: '+error;}}}}
async function submitForgot(){{const msg=document.getElementById('forgotMessage');msg.textContent='Sending...';try{{const response=await fetch('/api/auth/forgot-password',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:document.getElementById('forgotEmail').value}})}});const data=await response.json();msg.textContent=data.message||'If that email exists, a reset link has been sent.';}}catch(error){{msg.textContent='Request failed: '+error;}}}}
</script>
</body>
</html>
"""


def render_admin_login_page() -> str:
    auth = build_auth_summary()
    return f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>AI Software Factory — Platform Admin</title>
  <style>
{SHARED_STYLE}
    body {{ display: grid; place-items: center; }}
  </style>
</head>
<body>
  <div class='login-card'>
    <div class='brand' style='justify-content:center;font-size:18px'><span class='mark'></span><span>Mission Control</span></div>
    <div id='signinView'>
      <h2>Platform Admin Login</h2>
      <label>Founder email</label><input class='field' id='email' value='{escape(_founder_email_default())}' autocomplete='username' />
      <label>Password</label><input class='field' id='password' type='password' placeholder='FOUNDER_PASSWORD' autocomplete='current-password' />
      <div class='forgot-row'><a class='forgot-link' onclick='showForgot()'>Forgot password?</a></div>
      <button class='primary full' onclick='login()'>Enter Mission Control</button>
      <div id='loginError' class='error'></div>
      <p class='note'>Auth status: {escape(auth['status'])}.</p>
    </div>
    <div id='forgotView' style='display:none'>
      <h2>Reset your password</h2>
      <p style='text-align:center;color:#8a8d98;font-size:13px;margin-top:-6px'>Enter the platform admin email and we'll send a reset link.</p>
      <label>Email</label><input class='field' id='forgotEmail' value='{escape(_founder_email_default())}' autocomplete='username' />
      <button class='primary full' onclick='submitForgot()'>Send reset link</button>
      <div id='forgotMessage' class='note'></div>
      <p class='switch-mode'><a onclick='showSignin()'>Back to sign in</a></p>
    </div>
  </div>
<script>
function showForgot(){{document.getElementById('signinView').style.display='none';document.getElementById('forgotView').style.display='block';document.getElementById('forgotMessage').textContent='';}}
function showSignin(){{document.getElementById('forgotView').style.display='none';document.getElementById('signinView').style.display='block';}}
async function post(url,body){{const response=await fetch(url,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});return await response.json();}}
async function login(){{const data=await post('/mission-control/auth/login',{{email:document.getElementById('email').value,password:document.getElementById('password').value}});if(data.session&&data.session.token){{localStorage.setItem('mission_control_token',data.session.token);window.location.href='/mission-control/ui';}}else{{document.getElementById('loginError').textContent=data.status||'Login failed';}}}}
async function submitForgot(){{const msg=document.getElementById('forgotMessage');msg.textContent='Sending...';try{{const data=await post('/mission-control/auth/forgot-password',{{email:document.getElementById('forgotEmail').value}});msg.textContent=data.message||'If that email exists, a reset link has been sent.';}}catch(error){{msg.textContent='Request failed: '+error;}}}}
</script>
</body>
</html>
"""


def _founder_email_default() -> str:
    import os

    return os.getenv("FOUNDER_EMAIL", "founder@ai-software-factory.local")
