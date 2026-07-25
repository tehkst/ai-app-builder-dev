from __future__ import annotations


def render_builder() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>SaaS Builder</title><style>
:root{font-family:Inter,system-ui,sans-serif;color:#17201d;background:#f4f7f5}
*{box-sizing:border-box}body{margin:0}main{max-width:820px;margin:auto;padding:42px 22px}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:42px}
.brand{font-size:18px;font-weight:750}.account{color:#64706b;font-size:13px}
h1{font-size:40px;line-height:1.08;margin:0 0 12px;letter-spacing:0}
p{color:#52605a;line-height:1.55}.panel{background:white;border:1px solid #dbe3df;padding:24px;border-radius:8px}
label{display:block;font-size:13px;font-weight:700;margin:18px 0 7px}
input,textarea{width:100%;padding:12px;border:1px solid #bac7c1;border-radius:6px;font:inherit}
textarea{min-height:150px;resize:vertical}button,.button{display:inline-flex;align-items:center;justify-content:center;
padding:11px 16px;border:0;border-radius:6px;background:#176b4b;color:white;font-weight:700;cursor:pointer;text-decoration:none}
button[disabled]{opacity:.55}.muted{background:#e9eeeb;color:#28332e}.hidden{display:none}
.progress{height:8px;background:#e4eae7;margin:20px 0;border-radius:4px;overflow:hidden}
.progress span{display:block;height:100%;background:#1b8059;transition:width .25s}
.status{font-weight:750;font-size:20px}.error{color:#a32b20}
@media(max-width:600px){h1{font-size:32px}main{padding-top:24px}}
</style></head><body><main><header><div class="brand">AI Software Factory</div>
<div class="account" id="account">SaaS Builder</div></header>
<section id="auth" class="panel"><h1>Build your application</h1>
<p>Create an account, then describe the product you need.</p>
<label>Email</label><input id="email" type="email" autocomplete="email">
<label>Password</label><input id="password" type="password" autocomplete="current-password">
<label>Organization</label><input id="organization" value="My Business">
<p><button onclick="authenticate('register')">Create account</button>
 <button class="muted" onclick="authenticate('login')">Log in</button></p><p id="authError" class="error"></p></section>
<section id="builder" class="hidden"><h1>What would you like to build?</h1>
<p>Describe the customer and the essential workflow. We will handle the delivery details.</p>
<div class="panel"><label>Application name</label><input id="applicationName" value="Pawfect Appointments">
<label>Application description</label><textarea id="description">Build an appointment-booking SaaS for a dog-grooming business. The owner can register, create grooming services and manage bookings. Customers can choose a service and book an available time through a public page.</textarea>
<p><button id="buildButton" onclick="startBuild()">Build application</button></p><p id="buildError" class="error"></p></div></section>
<section id="progressPanel" class="panel hidden"><div class="status" id="status">Build started</div>
<p id="message"></p><div class="progress"><span id="progress" style="width:0"></span></div>
<p id="summary"></p><p id="references"></p><a id="openApp" class="button hidden" target="_blank">Open application</a></section>
<script>
let token=sessionStorage.getItem('saas_builder_token')||'', timer=null;
const $=id=>document.getElementById(id);
function showBuilder(email){$('auth').classList.add('hidden');$('builder').classList.remove('hidden');$('account').textContent=email}
async function authenticate(mode){$('authError').textContent='';const body={email:$('email').value,password:$('password').value};
if(mode==='register'){body.full_name='SaaS Builder User';body.organization_name=$('organization').value}
const response=await fetch('/api/auth/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const data=await response.json();if(!response.ok){$('authError').textContent=data.detail||'Authentication failed.';return}
token=data.access_token;sessionStorage.setItem('saas_builder_token',token);showBuilder(data.user.email)}
async function startBuild(){$('buildError').textContent='';$('buildButton').disabled=true;
const body={application_name:$('applicationName').value,description:$('description').value};
const response=await fetch('/api/saas-builder/builds',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify(body)});
const data=await response.json();if(!response.ok||!data.build){$('buildError').textContent=data.message||data.detail||'Build could not start.';$('buildButton').disabled=false;return}
history.replaceState({},'',location.pathname+'?run='+encodeURIComponent(data.build.workflow_run_id));render(data.build);poll(data.build.workflow_run_id)}
function render(build){$('builder').classList.add('hidden');$('progressPanel').classList.remove('hidden');$('status').textContent=build.status==='live'?'Your application is live':build.application_name;
$('message').textContent=build.message;$('progress').style.width=build.progress+'%';$('summary').textContent=build.build_summary||'';
$('references').textContent='Mission '+build.mission_id+' · Build '+build.workflow_run_id;
if(build.status==='live'&&build.live_url){$('openApp').href=build.live_url;$('openApp').classList.remove('hidden')}}
async function poll(run){clearTimeout(timer);const response=await fetch('/api/saas-builder/builds/'+encodeURIComponent(run),{headers:{'Authorization':'Bearer '+token}});
if(response.status===401){sessionStorage.removeItem('saas_builder_token');location.href='/saas-builder';return}
const data=await response.json();if(data.build){render(data.build);if(!['live','failed','blocked','cancelled'].includes(data.build.status))timer=setTimeout(()=>poll(run),1800)}}
async function resume(){if(!token)return;const me=await fetch('/api/auth/me',{headers:{'Authorization':'Bearer '+token}});if(!me.ok)return;
const user=await me.json();showBuilder(user.email);const run=new URLSearchParams(location.search).get('run');if(run)poll(run)}resume();
</script></main></body></html>"""
