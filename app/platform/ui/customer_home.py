from __future__ import annotations


def render_customer_home() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI Software Factory · Your Projects</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#2b2d33;background:#fbf7f2}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 50% 0,#fff 0,#fbf7f2 45%,#f6eee5 100%)}
a{color:inherit;text-decoration:none}
.topbar{height:70px;display:flex;align-items:center;justify-content:space-between;padding:0 6vw}
.brand{display:flex;align-items:center;gap:10px;font-weight:900;font-size:22px;letter-spacing:-.03em}
.mark{width:26px;height:26px;border-radius:8px;background:linear-gradient(135deg,#2b6df6,#6ee7ff)}
.logout{border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:999px;padding:9px 16px;font-weight:800;cursor:pointer}
main{max-width:760px;margin:0 auto;padding:40px 20px 80px}
.card{background:white;border:1px solid #eadfd5;border-radius:20px;padding:26px;margin-bottom:16px;box-shadow:0 18px 60px rgba(30,26,23,.06)}
.card-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:4px}
h1{font-size:32px;letter-spacing:-.03em;margin:0 0 6px}
h2{font-size:18px;margin:0 0 4px}
.muted{color:#8a8d98;font-size:14px}
.row{display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f1e9df;padding:12px 0;gap:12px}
.row:first-child{border-top:0}
.tag{display:inline-flex;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:800;background:#eaf1fe;color:#2b6df6;white-space:nowrap}
.tag-good{background:#e6f7ec;color:#1a7f37}
.tag-bad{background:#fdecec;color:#c93b3b}
label{display:block;font-size:13px;color:#686b75;margin:14px 0 6px}
.field{width:100%;border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:12px;padding:12px;font:inherit;resize:vertical}
.actions{display:flex;gap:10px;margin-top:14px}
button.primary{border:0;border-radius:12px;padding:12px 18px;font-weight:800;background:#2b6df6;color:white;cursor:pointer}
button.danger{border:1px solid #f1c9c9;background:#fff5f5;color:#c93b3b;border-radius:10px;padding:7px 12px;font-weight:700;cursor:pointer;font-size:12.5px}
.error{color:#cf3d3d;font-size:13px;margin-top:10px;min-height:18px}
.note{font-size:13px;margin-top:10px;color:#8a8d98}
.warn-banner{background:#fff7e6;border:1px solid #f2d999;color:#8a5a00;border-radius:12px;padding:12px 14px;font-size:13px;margin-bottom:14px}
.secret-name{font-weight:700}
.secret-meta{font-size:12px;color:#8a8d98}
.empty{color:#8a8d98;font-size:13px}
.project-row{cursor:pointer}
.project-row:hover{background:#fbf7f2}
.overlay{position:fixed;inset:0;background:rgba(20,16,12,.45);display:none;align-items:center;justify-content:center;z-index:50;padding:20px}
.overlay-card{width:min(560px,92vw);max-height:86vh;overflow-y:auto}
.sow{white-space:pre-wrap;font-size:13px;background:#faf6f1;border:1px solid #eadfd5;border-radius:12px;padding:14px;max-height:320px;overflow:auto;margin-top:10px}
</style>
</head>
<body>
<header class="topbar"><a class="brand" href="/"><span class="mark"></span><span>AI Software Factory</span></a><button class="logout" onclick="logout()">Logout</button></header>
<main>
<div class="card"><h1 id="welcomeHeading">Welcome</h1><p class="muted">This is your workspace home.</p></div>

<div class="card">
<div class="card-head"><h2>Your Projects</h2><button class="primary" onclick="openNewProject()">New Project</button></div>
<p class="muted">Apps you've asked the platform to build. Draft a scope, approve it, then start the build.</p>
<div id="projectsList"><p class="empty">Loading…</p></div>
</div>

<div class="card"><div class="row"><span>Email</span><span id="fieldEmail" class="tag">Loading…</span></div><div class="row"><span>Name</span><span id="fieldName" class="tag">Loading…</span></div></div>
<div class="card">
<h2>API Keys &amp; Secrets</h2>
<p class="muted">Store your own third-party API keys (OpenAI, Stripe, etc.) for use in your builds. Values are encrypted before they're ever saved and are never shown again — only the name and dates are kept visible.</p>
<div id="vaultWarning" class="warn-banner" style="display:none">Secret storage is not yet configured on this deployment. Saving is temporarily disabled.</div>
<div id="secretsList"><p class="empty">Loading…</p></div>
<label>Key name</label><input class="field" id="secretKeyName" placeholder="OPENAI_API_KEY" autocomplete="off"/>
<label>Value</label><input class="field" id="secretValue" type="password" placeholder="Paste the secret value" autocomplete="off"/>
<div class="actions"><button class="primary" id="saveSecretBtn" onclick="saveSecret()">Save secret</button></div>
<div id="secretError" class="error"></div>
</div>
</main>

<div id="newProjectOverlay" class="overlay">
<div class="card overlay-card">
<h2>Describe your app</h2>
<label>What do you want to build?</label>
<textarea class="field" id="newProjectIdea" rows="4" placeholder="e.g. A booking app for a yoga studio with class schedules and student check-in"></textarea>
<div class="actions"><button class="primary" onclick="submitNewProject()">Draft scope</button><button class="danger" onclick="closeOverlay('newProjectOverlay')">Cancel</button></div>
<div id="newProjectError" class="error"></div>
</div>
</div>

<div id="projectDetailOverlay" class="overlay">
<div class="card overlay-card">
<div class="card-head"><h2 id="detailName">Project</h2><button class="danger" onclick="closeOverlay('projectDetailOverlay')">Close</button></div>
<p class="muted" id="detailMeta"></p>
<div id="detailActions" class="actions"></div>
<div id="detailBuildStatus"></div>
<div id="detailSow" class="sow"></div>
<div id="detailError" class="error"></div>
</div>
</div>

<script>
(function(){
var token=localStorage.getItem('customer_token')||'';
if(!token){window.location.href='/';return}
function authHeaders(){return {'Authorization':'Bearer '+token,'Content-Type':'application/json'}}
fetch('/api/auth/me',{headers:authHeaders()}).then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(function(data){
document.getElementById('welcomeHeading').textContent='Welcome, '+(data.full_name||data.email);
document.getElementById('fieldEmail').textContent=data.email||'Unknown';
document.getElementById('fieldName').textContent=data.full_name||'Unknown';
}).catch(function(){window.location.href='/'});
window.logout=function(){localStorage.removeItem('customer_token');window.location.href='/'};

function escapeHtml(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}

function statusBadge(project){
  var build=project.build;
  if(build){
    if(build.failed_step_count){return {text:'Build failed',cls:'tag-bad'}}
    if(build.plan_status==='completed'){return {text:'Built',cls:'tag-good'}}
    return {text:'Building…',cls:'tag'};
  }
  if(project.approval_status==='scope_approved'){return {text:'Approved — ready to build',cls:'tag'}}
  return {text:'Draft — needs approval',cls:'tag'};
}

function renderProjects(list){
  var el=document.getElementById('projectsList');
  if(!list.length){el.innerHTML='<p class="empty">No projects yet. Click "New Project" to describe your first app.</p>';return}
  el.innerHTML='';
  list.forEach(function(project){
    var badge=statusBadge(project);
    var row=document.createElement('div');
    row.className='row project-row';
    row.onclick=function(){openProjectDetail(project.scoping_request_id)};
    row.innerHTML='<div><div class="secret-name">'+escapeHtml(project.name)+'</div><div class="secret-meta">v'+project.version+' · updated '+new Date(project.updated_at).toLocaleString()+'</div></div><span class="tag '+badge.cls+'">'+escapeHtml(badge.text)+'</span>';
    el.appendChild(row);
  });
}

window.refreshProjects=function(){
  fetch('/api/projects',{headers:authHeaders()}).then(function(r){return r.json()}).then(function(data){renderProjects(data.projects||[])}).catch(function(){
    document.getElementById('projectsList').innerHTML='<p class="empty">Could not load projects.</p>';
  });
};

window.openNewProject=function(){
  document.getElementById('newProjectIdea').value='';
  document.getElementById('newProjectError').textContent='';
  document.getElementById('newProjectOverlay').style.display='flex';
};
window.closeOverlay=function(id){document.getElementById(id).style.display='none'};

window.submitNewProject=async function(){
  var err=document.getElementById('newProjectError');err.textContent='';
  var idea=document.getElementById('newProjectIdea').value.trim();
  if(!idea){err.textContent='Describe what you want to build first.';return}
  try{
    var response=await fetch('/api/projects/draft-scope',{method:'POST',headers:authHeaders(),body:JSON.stringify({app_request:idea})});
    var data=await response.json();
    if(!response.ok||!data.success){err.textContent=data.message||data.detail||'Could not draft a scope.';return}
    closeOverlay('newProjectOverlay');
    refreshProjects();
    openProjectDetail(data.scoping_request_id);
  }catch(error){err.textContent='Request failed: '+error}
};

window.openProjectDetail=async function(scopingRequestId){
  var overlay=document.getElementById('projectDetailOverlay');
  document.getElementById('detailError').textContent='';
  document.getElementById('detailSow').textContent='Loading…';
  document.getElementById('detailActions').innerHTML='';
  document.getElementById('detailBuildStatus').innerHTML='';
  overlay.style.display='flex';
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(scopingRequestId),{headers:authHeaders()});
    var data=await response.json();
    if(!response.ok||!data.success){document.getElementById('detailError').textContent=data.detail||'Could not load project.';return}
    renderProjectDetail(data);
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error}
};

function renderProjectDetail(data){
  var appIdea=(data.normalized_request||{}).app_idea||'Untitled project';
  document.getElementById('detailName').textContent=appIdea.length>60?appIdea.slice(0,57)+'...':appIdea;
  document.getElementById('detailMeta').textContent='v'+data.version+' · '+data.approval_status;
  document.getElementById('detailSow').textContent=data.scope_of_work_markdown||'No scope drafted yet.';

  var actions=document.getElementById('detailActions');
  actions.innerHTML='';
  var buildStatus=document.getElementById('detailBuildStatus');
  buildStatus.innerHTML='';

  if(data.approval_status!=='scope_approved'){
    var approveBtn=document.createElement('button');
    approveBtn.className='primary';approveBtn.textContent='Approve scope';
    approveBtn.onclick=function(){approveProject(data.scoping_request_id)};
    actions.appendChild(approveBtn);
  }else if(!data.build){
    var buildBtn=document.createElement('button');
    buildBtn.className='primary';buildBtn.textContent='Start build';
    buildBtn.onclick=function(){buildProject(data.scoping_request_id)};
    actions.appendChild(buildBtn);
  }else{
    var build=data.build;
    var text='Build status: '+(build.plan_status||build.status||'unknown')+' ('+(build.completed_step_count||0)+'/'+(build.step_count||0)+' steps complete';
    if(build.failed_step_count){text+=', '+build.failed_step_count+' failed'}
    text+='). No live deployment URL is wired up for customer builds yet — this reflects build/generation status only.';
    buildStatus.innerHTML='<p class="note">'+escapeHtml(text)+'</p>';
  }
}

window.approveProject=async function(scopingRequestId){
  document.getElementById('detailError').textContent='';
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(scopingRequestId)+'/approve',{method:'POST',headers:authHeaders()});
    var data=await response.json();
    if(!response.ok||!data.success){document.getElementById('detailError').textContent=data.detail||'Could not approve.';return}
    refreshProjects();
    openProjectDetail(scopingRequestId);
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error}
};

window.buildProject=async function(scopingRequestId){
  document.getElementById('detailBuildStatus').innerHTML='<p class="note">Building…</p>';
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(scopingRequestId)+'/build',{method:'POST',headers:authHeaders(),body:JSON.stringify({})});
    var data=await response.json();
    if(!data.success){document.getElementById('detailError').textContent=data.reason||data.detail||'Build failed to start.'}
    refreshProjects();
    openProjectDetail(scopingRequestId);
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error}
};

function renderSecrets(data){
  var list=document.getElementById('secretsList');
  var warning=document.getElementById('vaultWarning');
  warning.style.display=data.configured?'none':'block';
  document.getElementById('saveSecretBtn').disabled=!data.configured;
  var secrets=data.secrets||[];
  if(!secrets.length){list.innerHTML='<p class="empty">No secrets stored yet.</p>';return}
  list.innerHTML='';
  secrets.forEach(function(secret){
    var row=document.createElement('div');
    row.className='row';
    var meta='Added '+new Date(secret.created_at).toLocaleDateString()+(secret.last_used_at?(' · last used '+new Date(secret.last_used_at).toLocaleDateString()):' · never used');
    row.innerHTML='<div><div class="secret-name">'+escapeHtml(secret.key_name)+'</div><div class="secret-meta">'+escapeHtml(meta)+'</div></div><div><span class="tag">••••••••</span> <button class="danger" onclick="deleteSecret(\\''+escapeHtml(secret.key_name)+'\\')">Delete</button></div>';
    list.appendChild(row);
  });
}
window.refreshSecrets=function(){
  fetch('/api/secrets',{headers:authHeaders()}).then(function(r){return r.json()}).then(renderSecrets).catch(function(){
    document.getElementById('secretsList').innerHTML='<p class="empty">Could not load secrets.</p>';
  });
};
window.saveSecret=async function(){
  var err=document.getElementById('secretError');err.textContent='';
  var keyName=document.getElementById('secretKeyName').value.trim();
  var value=document.getElementById('secretValue').value;
  try{
    var response=await fetch('/api/secrets',{method:'POST',headers:authHeaders(),body:JSON.stringify({key_name:keyName,value:value})});
    var data=await response.json();
    if(!response.ok){err.textContent=data.detail||'Could not save secret.';return}
    document.getElementById('secretKeyName').value='';
    document.getElementById('secretValue').value='';
    refreshSecrets();
  }catch(error){err.textContent='Request failed: '+error}
};
window.deleteSecret=async function(keyName){
  if(!confirm('Delete '+keyName+'? This cannot be undone.'))return;
  try{
    await fetch('/api/secrets/'+encodeURIComponent(keyName),{method:'DELETE',headers:authHeaders()});
    refreshSecrets();
  }catch(error){}
};
refreshProjects();
refreshSecrets();
})();
</script>
</body>
</html>
"""
