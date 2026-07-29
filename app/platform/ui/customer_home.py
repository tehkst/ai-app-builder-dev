from __future__ import annotations


def render_customer_home() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI Software Factory · Your Workspace</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#2b2d33;background:#fbf7f2}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:#fbf7f2;display:flex}
a{color:inherit;text-decoration:none}
button{font:inherit;cursor:pointer}

.sidebar{width:250px;flex:0 0 250px;background:#fffaf5;border-right:1px solid #eadfd5;min-height:100vh;display:flex;flex-direction:column;padding:18px 14px;position:sticky;top:0;align-self:flex-start}
.brand{display:flex;align-items:center;gap:10px;font-weight:900;font-size:17px;letter-spacing:-.03em;padding:6px 8px 18px}
.mark{width:24px;height:24px;border-radius:7px;background:linear-gradient(135deg,#2b6df6,#6ee7ff);flex:none}
.nav{display:flex;flex-direction:column;gap:2px}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:10px;font-size:14px;font-weight:600;color:#55585f;border:0;background:none;text-align:left;width:100%}
.nav-item:hover{background:#f6eee5}
.nav-item.active{background:#eaf1fe;color:#2b6df6}
.nav-item .soon{margin-left:auto;font-size:10px;font-weight:800;color:#a8abb3;background:#f1e9df;border-radius:999px;padding:2px 7px}
.sidebar-foot{margin-top:auto;padding-top:14px;border-top:1px solid #f1e9df}
.logout{width:100%;border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:10px;padding:9px 12px;font-weight:800;font-size:13px}

main{flex:1;min-width:0;padding:44px 5vw 80px;background:radial-gradient(circle at 50% 0,#fff 0,#fbf7f2 45%,#f6eee5 100%)}
.view{display:none;max-width:920px;margin:0 auto}
.view.active{display:block}

h1.hero{font-size:30px;letter-spacing:-.03em;text-align:center;margin:0 0 22px}
.composer{background:white;border:1px solid #eadfd5;border-radius:20px;padding:16px 18px;box-shadow:0 18px 60px rgba(30,26,23,.06)}
.composer textarea{width:100%;border:0;outline:0;resize:none;font:inherit;font-size:15px;min-height:52px;background:transparent}
.composer-row{display:flex;align-items:center;gap:10px;margin-top:6px}
.icon-btn{width:34px;height:34px;border-radius:10px;border:1px solid #eadfd5;background:#faf6f1;color:#a8abb3;display:inline-flex;align-items:center;justify-content:center;font-size:16px}
.icon-btn[disabled]{cursor:not-allowed}
.spacer{flex:1}
.send-btn{width:36px;height:36px;border-radius:999px;border:0;background:#2b6df6;color:white;font-size:16px;display:inline-flex;align-items:center;justify-content:center}
.send-btn:disabled{background:#c9d8f8;cursor:not-allowed}

.chip-row{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin:18px 0}
.chip{border:1px solid #eadfd5;background:white;border-radius:999px;padding:8px 14px;font-size:13px;font-weight:700;color:#55585f}
.chip:hover{background:#f6eee5}
.chip-label{text-align:center;color:#8a8d98;font-size:13px;margin-top:20px}

.section-title{display:flex;justify-content:space-between;align-items:center;margin:34px 0 12px}
.section-title h2{font-size:18px;margin:0}

.card{background:white;border:1px solid #eadfd5;border-radius:20px;padding:26px;margin-bottom:16px;box-shadow:0 18px 60px rgba(30,26,23,.06)}
.card-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:4px}
h2{font-size:18px;margin:0 0 4px}
.muted{color:#8a8d98;font-size:14px}
.empty{color:#8a8d98;font-size:13px}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}
.proj-card{background:white;border:1px solid #eadfd5;border-radius:16px;padding:16px;cursor:pointer;display:flex;flex-direction:column;gap:10px}
.proj-card:hover{border-color:#c9d8f8;box-shadow:0 10px 30px rgba(43,109,246,.08)}
.proj-icon{width:40px;height:40px;border-radius:11px;background:linear-gradient(135deg,#2b6df6,#6ee7ff);color:white;font-weight:900;display:flex;align-items:center;justify-content:center;font-size:16px}
.proj-name{font-weight:800;font-size:14px;line-height:1.3}
.proj-meta{font-size:12px;color:#8a8d98}
.tag{display:inline-flex;border-radius:999px;padding:3px 9px;font-size:11px;font-weight:800;background:#eaf1fe;color:#2b6df6;white-space:nowrap;align-self:flex-start}
.tag-good{background:#e6f7ec;color:#1a7f37}
.tag-bad{background:#fdecec;color:#c93b3b}

.row{display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f1e9df;padding:12px 0;gap:12px}
.row:first-child{border-top:0}
label{display:block;font-size:13px;color:#686b75;margin:14px 0 6px}
.field{width:100%;border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:12px;padding:12px;font:inherit;resize:vertical}
.actions{display:flex;gap:10px;margin-top:14px}
button.primary{border:0;border-radius:12px;padding:12px 18px;font-weight:800;background:#2b6df6;color:white}
button.danger{border:1px solid #f1c9c9;background:#fff5f5;color:#c93b3b;border-radius:10px;padding:7px 12px;font-weight:700;font-size:12.5px}
.error{color:#cf3d3d;font-size:13px;margin-top:10px;min-height:18px}
.note{font-size:13px;margin-top:10px;color:#8a8d98}
.warn-banner{background:#fff7e6;border:1px solid #f2d999;color:#8a5a00;border-radius:12px;padding:12px 14px;font-size:13px;margin-bottom:14px}
.secret-name{font-weight:700}
.secret-meta{font-size:12px;color:#8a8d98}

.overlay{position:fixed;inset:0;background:rgba(20,16,12,.45);display:none;align-items:center;justify-content:center;z-index:50;padding:20px}
.overlay-card{width:min(560px,92vw);max-height:86vh;overflow-y:auto}
.sow{white-space:pre-wrap;font-size:13px;background:#faf6f1;border:1px solid #eadfd5;border-radius:12px;padding:14px;max-height:320px;overflow:auto;margin-top:10px}
</style>
</head>
<body>

<nav class="sidebar">
<div class="brand"><span class="mark"></span><span>AI Software Factory</span></div>
<div class="nav">
<button class="nav-item active" data-section="home">Home</button>
<button class="nav-item" data-section="projects">Projects</button>
<button class="nav-item" data-section="published">Published Projects</button>
<button class="nav-item" data-section="integrations">Integrations<span class="soon">Soon</span></button>
<button class="nav-item" data-section="security">Security<span class="soon">Soon</span></button>
<button class="nav-item" data-section="promotions">Promotions<span class="soon">Soon</span></button>
<button class="nav-item" data-section="settings">Settings</button>
</div>
<div class="sidebar-foot"><button class="logout" onclick="logout()">Log out</button></div>
</nav>

<main>

<section class="view active" id="view-home">
<h1 class="hero" id="homeGreeting">Hi, what do you want to make?</h1>
<div class="composer">
<textarea id="composerInput" rows="2" placeholder="Describe the app you want to build..."></textarea>
<div class="composer-row">
<button class="icon-btn" disabled title="Attachments aren't supported yet">+</button>
<button class="icon-btn" disabled title="Voice input isn't supported yet">&#127908;</button>
<div class="spacer"></div>
<button class="send-btn" id="composerSendBtn" onclick="submitComposer()">&#8593;</button>
</div>
</div>
<div class="chip-row" id="kindChips">
<button class="chip" data-prefix="Build a website that ">Website</button>
<button class="chip" data-prefix="Build a mobile-friendly app that ">Mobile-friendly app</button>
<button class="chip" data-prefix="Build an internal tool that ">Internal tool</button>
</div>
<p class="chip-label">Try an example prompt</p>
<div class="chip-row" id="exampleChips">
<button class="chip" data-text="Build a booking app for a yoga studio with class schedules and student check-in">Studio booking app</button>
<button class="chip" data-text="Build a personal budget tracker with monthly spending categories">Budget tracker</button>
<button class="chip" data-text="Build a customer feedback portal where customers submit and vote on ideas">Feedback portal</button>
</div>
<div id="composerError" class="error" style="text-align:center"></div>

<div class="section-title"><h2>Your recent Projects</h2></div>
<div id="recentProjectsGrid" class="grid"><p class="empty">Loading…</p></div>
</section>

<section class="view" id="view-projects">
<div class="section-title"><h2>Your Projects</h2><button class="primary" onclick="goToHomeComposer()">New Project</button></div>
<p class="muted">Apps you've asked the platform to build. Draft a scope, approve it, then start the build.</p>
<div id="allProjectsGrid" class="grid"><p class="empty">Loading…</p></div>
</section>

<section class="view" id="view-published">
<div class="section-title"><h2>Published Projects</h2></div>
<p class="muted">Projects whose build has completed. There is no live deployment URL wired up for these yet - this shows build completion only.</p>
<div id="publishedProjectsGrid" class="grid"><p class="empty">Loading…</p></div>
</section>

<section class="view" id="view-integrations">
<div class="card"><h2>Integrations</h2><p class="muted">Connecting third-party services to your builds isn't available yet.</p></div>
</section>

<section class="view" id="view-security">
<div class="card"><h2>Security</h2><p class="muted">Team roles and access controls aren't available yet.</p></div>
</section>

<section class="view" id="view-promotions">
<div class="card"><h2>Promotions</h2><p class="muted">There are no active promotions or plan upgrades available yet.</p></div>
</section>

<section class="view" id="view-settings">
<div class="card"><div class="row"><span>Email</span><span id="fieldEmail" class="tag">Loading…</span></div><div class="row"><span>Name</span><span id="fieldName" class="tag">Loading…</span></div></div>
<div class="card">
<h2>API Keys &amp; Secrets</h2>
<p class="muted">Store your own third-party API keys (OpenAI, Stripe, etc.) for use in your builds. Values are encrypted before they're ever saved and are never shown again — only the name and dates are kept visible.</p>
<div id="vaultWarning" class="warn-banner" style="display:none">Secret storage is not yet configured on this deployment. Saving is temporarily disabled.</div>
<div id="secretsList"><p class="empty">Loading…</p></div>
<label>Key name</label><input class="field" id="secretKeyName" placeholder="OPENAI_API_KEY" autocomplete="off"/>
<label>Value</label><input class="field" id="secretValue" type="password" placeholder="Paste the secret value" autocomplete="new-password"/>
<div class="actions"><button class="primary" id="saveSecretBtn" onclick="saveSecret()">Save secret</button></div>
<div id="secretError" class="error"></div>
</div>
</section>

</main>

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
function escapeHtml(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}

// ---- navigation ----
function showSection(name){
  Array.from(document.querySelectorAll('.view')).forEach(function(el){el.classList.remove('active')});
  Array.from(document.querySelectorAll('.nav-item')).forEach(function(el){el.classList.remove('active')});
  var view=document.getElementById('view-'+name); if(view)view.classList.add('active');
  var navItem=document.querySelector('.nav-item[data-section="'+name+'"]'); if(navItem)navItem.classList.add('active');
}
Array.from(document.querySelectorAll('.nav-item')).forEach(function(btn){
  btn.addEventListener('click',function(){showSection(btn.dataset.section)});
});
window.goToHomeComposer=function(){showSection('home');document.getElementById('composerInput').focus()};
window.logout=function(){localStorage.removeItem('customer_token');window.location.href='/'};

// ---- profile ----
fetch('/api/auth/me',{headers:authHeaders()}).then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(function(data){
  var name=data.full_name||data.email;
  document.getElementById('homeGreeting').textContent='Hi '+name.split(' ')[0]+', what do you want to make?';
  document.getElementById('fieldEmail').textContent=data.email||'Unknown';
  document.getElementById('fieldName').textContent=data.full_name||'Unknown';
}).catch(function(){window.location.href='/'});

// ---- composer ----
Array.from(document.querySelectorAll('#kindChips .chip')).forEach(function(btn){
  btn.addEventListener('click',function(){
    var input=document.getElementById('composerInput');
    input.value=btn.dataset.prefix;
    input.focus();
  });
});
Array.from(document.querySelectorAll('#exampleChips .chip')).forEach(function(btn){
  btn.addEventListener('click',function(){
    document.getElementById('composerInput').value=btn.dataset.text;
    document.getElementById('composerInput').focus();
  });
});
window.submitComposer=async function(){
  var err=document.getElementById('composerError');err.textContent='';
  var input=document.getElementById('composerInput');
  var idea=input.value.trim();
  if(!idea){err.textContent='Describe what you want to build first.';return}
  var btn=document.getElementById('composerSendBtn');
  btn.disabled=true;
  try{
    var response=await fetch('/api/projects/draft-scope',{method:'POST',headers:authHeaders(),body:JSON.stringify({app_request:idea})});
    var data=await response.json();
    if(!response.ok||!data.success){err.textContent=data.message||data.detail||'Could not draft a scope.';return}
    input.value='';
    refreshProjects();
    openProjectDetail(data.scoping_request_id);
  }catch(error){err.textContent='Request failed: '+error}
  finally{btn.disabled=false}
};

// ---- project grids ----
var allProjects=[];

function timeAgo(iso){
  if(!iso)return '';
  var seconds=Math.max(0,Math.floor((Date.now()-new Date(iso).getTime())/1000));
  var units=[[31536000,'year'],[2592000,'month'],[86400,'day'],[3600,'hour'],[60,'minute']];
  for(var i=0;i<units.length;i++){
    var value=Math.floor(seconds/units[i][0]);
    if(value>=1)return value+' '+units[i][1]+(value>1?'s':'')+' ago';
  }
  return 'just now';
}

function humanizeStatus(status){
  return String(status||'draft').replace(/_/g,' ').replace(/\b\w/g,function(c){return c.toUpperCase()});
}

function statusBadge(project){
  if(project.source==='saas_builder'){
    if(project.status==='blocked'||project.status==='failed'){return {text:'Build failed',cls:'tag-bad'}}
    if(project.status==='live'){return {text:'Live',cls:'tag-good'}}
    return {text:humanizeStatus(project.status),cls:'tag'};
  }
  var build=project.build;
  if(build){
    if(build.failed_step_count){return {text:'Build failed',cls:'tag-bad'}}
    if(build.plan_status==='completed'){return {text:'Built',cls:'tag-good'}}
    return {text:'Building…',cls:'tag'};
  }
  if(project.approval_status==='scope_approved'){return {text:'Approved',cls:'tag'}}
  return {text:'Draft',cls:'tag'};
}

function projectCardHtml(project){
  var badge=statusBadge(project);
  var initial=(project.name||'?').trim().charAt(0).toUpperCase()||'?';
  return '<div class="proj-card" data-id="'+project.id+'">'
    +'<div class="proj-icon">'+escapeHtml(initial)+'</div>'
    +'<div class="proj-name">'+escapeHtml(project.name)+'</div>'
    +'<div class="proj-meta">'+timeAgo(project.updated_at)+'</div>'
    +'<span class="tag '+badge.cls+'">'+escapeHtml(badge.text)+'</span>'
    +'</div>';
}

function renderGrid(elementId, projects, emptyMessage){
  var el=document.getElementById(elementId);
  if(!projects.length){el.innerHTML='<p class="empty">'+emptyMessage+'</p>';return}
  el.innerHTML=projects.map(projectCardHtml).join('');
  Array.from(el.querySelectorAll('.proj-card')).forEach(function(card){
    card.addEventListener('click',function(){openProjectDetail(card.dataset.id)});
  });
}

window.refreshProjects=function(){
  fetch('/api/projects',{headers:authHeaders()}).then(function(r){return r.json()}).then(function(data){
    allProjects=data.projects||[];
    renderGrid('recentProjectsGrid', allProjects.slice(0,6), 'No projects yet. Describe an app above to get started.');
    renderGrid('allProjectsGrid', allProjects, 'No projects yet. Click "New Project" to describe your first app.');
    var published=allProjects.filter(function(p){return (p.build&&p.build.plan_status==='completed')||(p.source==='saas_builder'&&p.status==='live')});
    renderGrid('publishedProjectsGrid', published, 'No projects have a completed build yet.');
  }).catch(function(){
    document.getElementById('recentProjectsGrid').innerHTML='<p class="empty">Could not load projects.</p>';
    document.getElementById('allProjectsGrid').innerHTML='<p class="empty">Could not load projects.</p>';
    document.getElementById('publishedProjectsGrid').innerHTML='<p class="empty">Could not load projects.</p>';
  });
};

// ---- project detail overlay ----
window.closeOverlay=function(id){document.getElementById(id).style.display='none'};

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
  var actions=document.getElementById('detailActions');
  actions.innerHTML='';
  var buildStatus=document.getElementById('detailBuildStatus');
  buildStatus.innerHTML='';
  var sowBox=document.getElementById('detailSow');

  if(data.source==='saas_builder'){
    document.getElementById('detailName').textContent=data.application_name||'Untitled project';
    document.getElementById('detailMeta').textContent=humanizeStatus(data.status);
    sowBox.style.display='none';
    var html='<p class="note">'+escapeHtml(data.message||'')+'</p>';
    if(data.live_url){
      html+='<p class="note"><a href="'+escapeHtml(data.live_url)+'" target="_blank" rel="noopener">Open live app &rarr;</a></p>';
    }
    buildStatus.innerHTML=html;
    return;
  }
  sowBox.style.display='block';

  var appIdea=(data.normalized_request||{}).app_idea||'Untitled project';
  document.getElementById('detailName').textContent=appIdea.length>60?appIdea.slice(0,57)+'...':appIdea;
  document.getElementById('detailMeta').textContent='v'+data.version+' · '+data.approval_status;
  document.getElementById('detailSow').textContent=data.scope_of_work_markdown||'No scope drafted yet.';

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

// ---- secrets vault (Settings) ----
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
