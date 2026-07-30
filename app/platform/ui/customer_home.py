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
button.primary:disabled{background:#c9d8f8;cursor:not-allowed}
button.danger{border:1px solid #f1c9c9;background:#fff5f5;color:#c93b3b;border-radius:10px;padding:7px 12px;font-weight:700;font-size:12.5px}
.error{color:#cf3d3d;font-size:13px;margin-top:10px;min-height:18px}
.note{font-size:13px;margin-top:10px;color:#8a8d98}
.warn-banner{background:#fff7e6;border:1px solid #f2d999;color:#8a5a00;border-radius:12px;padding:12px 14px;font-size:13px;margin-bottom:14px}
.secret-name{font-weight:700}
.secret-meta{font-size:12px;color:#8a8d98}

.sow{white-space:pre-wrap;font-size:13px;background:#faf6f1;border:1px solid #eadfd5;border-radius:12px;padding:14px;max-height:420px;overflow:auto;margin-top:10px}

.project-head{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.project-head .proj-icon{width:44px;height:44px;font-size:18px}
.project-head-text{flex:1;min-width:0}
.project-head-text h1{font-size:20px;margin:0 0 4px;letter-spacing:-.02em}
.back-btn{border:1px solid #eadfd5;background:white;color:#55585f;border-radius:10px;padding:8px 14px;font-weight:700;font-size:13px}
.open-live-btn{border:0;background:#2b6df6;color:white;border-radius:10px;padding:9px 16px;font-weight:800;font-size:13px}
.tabs{display:flex;gap:4px;border-bottom:1px solid #eadfd5;margin:22px 0 18px}
.tab-btn{border:0;background:none;padding:10px 4px;margin-right:22px;font-weight:700;font-size:14px;color:#8a8d98;border-bottom:2px solid transparent}
.tab-btn.active{color:#2b6df6;border-bottom-color:#2b6df6}
.tab-pane{display:none}
.tab-pane.active{display:block}
.preview-frame-wrap{border:1px solid #eadfd5;border-radius:16px;overflow:hidden;background:white;box-shadow:0 18px 60px rgba(30,26,23,.06)}
.preview-frame-wrap iframe{width:100%;height:70vh;border:0;display:block}
.preview-empty{text-align:center;padding:60px 20px;color:#8a8d98;background:white;border:1px solid #eadfd5;border-radius:16px}
.preview-empty .big{font-size:15px;color:#55585f;font-weight:700;margin-bottom:6px}
.progress-track{background:#f1e9df;border-radius:999px;height:8px;overflow:hidden;margin:14px 0}
.progress-fill{background:#2b6df6;height:100%;border-radius:999px;transition:width .3s}
.stage-label{font-size:13px;color:#55585f;font-weight:700}
.step-list{margin-top:14px;display:flex;flex-direction:column;gap:6px}
.step-row{display:flex;align-items:center;gap:10px;font-size:13px;color:#686b75}
.step-icon{width:18px;height:18px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;background:#f1e9df;color:#8a8d98;flex:none}
.step-completed .step-icon{background:#e6f7ec;color:#1a7f37}
.step-failed .step-icon{background:#fdecec;color:#c93b3b}
.step-blocked .step-icon{background:#fff7e6;color:#8a5a00}
.step-completed,.step-failed{color:#2b2d33}
.elapsed-clock{font-variant-numeric:tabular-nums;font-weight:700}
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


<section class="view" id="view-project">
<div class="project-head">
<button class="back-btn" onclick="closeProjectDetail()">&larr; Back</button>
<div class="proj-icon" id="detailIcon">?</div>
<div class="project-head-text">
<h1 id="detailName">Project</h1>
<p class="muted" id="detailMeta"></p>
</div>
<a id="detailOpenLive" class="open-live-btn" href="#" target="_blank" rel="noopener" style="display:none">Open live app &rarr;</a>
<button id="detailDeleteBtn" class="danger" style="display:none" onclick="deleteProject()">Delete</button>
</div>
<div id="detailActions" class="actions"></div>
<div id="detailError" class="error"></div>

<div class="tabs">
<button class="tab-btn active" data-tab="preview" onclick="showDetailTab('preview')">Preview</button>
<button class="tab-btn" data-tab="details" onclick="showDetailTab('details')">Details</button>
</div>

<div class="tab-pane active" id="tab-preview">
<div id="detailPreview"></div>
</div>
<div class="tab-pane" id="tab-details">
<div id="detailBuildStatus"></div>
<div id="detailSow" class="sow" style="display:none"></div>
<div id="detailAmendBox" style="display:none">
<label>Request a change</label>
<textarea class="field" id="amendInput" rows="2" placeholder="Describe what to change about this scope..."></textarea>
<div class="actions"><button class="primary" id="amendSendBtn" onclick="submitAmend()">Send</button></div>
</div>
</div>
</section>

</main>

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
  return String(status||'draft').replace(/_/g,' ').replace(/\\b\\w/g,function(c){return c.toUpperCase()});
}

function statusBadge(project){
  if(project.source==='saas_builder'){
    if(project.status==='blocked'||project.status==='failed'){return {text:'Build failed',cls:'tag-bad'}}
    if(project.status==='live'){return {text:'Live',cls:'tag-good'}}
    return {text:humanizeStatus(project.status),cls:'tag'};
  }
  var build=project.build;
  if(build){
    // status is the real execution outcome ("completed"/"failed"/"blocked"...);
    // plan_status only reflects whether a plan was successfully drafted, so it
    // stays something like "ready" even after the build finished - checking it
    // here made a fully-finished build show "Building..." forever.
    if(build.failed_step_count){return {text:'Build failed',cls:'tag-bad'}}
    if(build.status==='completed'){return {text:'Built',cls:'tag-good'}}
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
    var published=allProjects.filter(function(p){return (p.build&&p.build.status==='completed')||(p.source==='saas_builder'&&p.status==='live')});
    renderGrid('publishedProjectsGrid', published, 'No projects have a completed build yet.');
  }).catch(function(){
    document.getElementById('recentProjectsGrid').innerHTML='<p class="empty">Could not load projects.</p>';
    document.getElementById('allProjectsGrid').innerHTML='<p class="empty">Could not load projects.</p>';
    document.getElementById('publishedProjectsGrid').innerHTML='<p class="empty">Could not load projects.</p>';
  });
};

// ---- project detail (full workspace page) ----
var previousSection='home';
var currentDetailId=null;

window.closeProjectDetail=function(){showSection(previousSection)};

window.showDetailTab=function(name){
  Array.from(document.querySelectorAll('.tab-btn')).forEach(function(el){el.classList.remove('active')});
  Array.from(document.querySelectorAll('.tab-pane')).forEach(function(el){el.classList.remove('active')});
  document.querySelector('.tab-btn[data-tab="'+name+'"]').classList.add('active');
  document.getElementById('tab-'+name).classList.add('active');
};

window.openProjectDetail=async function(scopingRequestId){
  previousSection=Array.from(document.querySelectorAll('.view.active')).map(function(el){return el.id.replace('view-','')})[0]||'home';
  currentDetailId=scopingRequestId;
  document.getElementById('detailError').textContent='';
  document.getElementById('detailPreview').innerHTML='<p class="empty">Loading…</p>';
  document.getElementById('detailActions').innerHTML='';
  document.getElementById('detailBuildStatus').innerHTML='';
  document.getElementById('detailSow').style.display='none';
  document.getElementById('detailOpenLive').style.display='none';
  document.getElementById('detailDeleteBtn').style.display='none';
  document.getElementById('detailAmendBox').style.display='none';
  document.getElementById('amendInput').value='';
  document.getElementById('detailName').textContent='Loading…';
  document.getElementById('detailMeta').textContent='';
  showDetailTab('preview');
  showSection('project');
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(scopingRequestId),{headers:authHeaders()});
    var data=await response.json();
    if(!response.ok||!data.success){document.getElementById('detailError').textContent=data.detail||'Could not load project.';return}
    renderProjectDetail(data);
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error}
};

function renderPreview(liveUrl, emptyMessage){
  var box=document.getElementById('detailPreview');
  if(liveUrl){
    box.innerHTML='<div class="preview-frame-wrap"><iframe src="'+escapeHtml(liveUrl)+'" title="Live app preview"></iframe></div>';
    var openLive=document.getElementById('detailOpenLive');
    openLive.href=liveUrl;
    openLive.style.display='inline-block';
  }else{
    box.innerHTML='<div class="preview-empty"><p class="big">No live preview yet</p><p>'+escapeHtml(emptyMessage)+'</p></div>';
  }
}

function renderProjectDetail(data){
  var actions=document.getElementById('detailActions');
  actions.innerHTML='';
  var buildStatus=document.getElementById('detailBuildStatus');
  buildStatus.innerHTML='';
  var sowBox=document.getElementById('detailSow');
  var icon=document.getElementById('detailIcon');

  if(data.source==='saas_builder'){
    var name=data.application_name||'Untitled project';
    icon.textContent=name.trim().charAt(0).toUpperCase()||'?';
    document.getElementById('detailName').textContent=name;
    document.getElementById('detailMeta').textContent=humanizeStatus(data.status);
    sowBox.style.display='none';

    renderPreview(data.live_url, data.message||'This application has not been deployed to a live URL yet.');

    var progress=typeof data.progress==='number'?data.progress:0;
    buildStatus.innerHTML='<p class="stage-label">'+escapeHtml(humanizeStatus(data.mission_stage||data.status))+'</p>'
      +'<div class="progress-track"><div class="progress-fill" style="width:'+progress+'%"></div></div>'
      +'<p class="note">'+escapeHtml(data.message||'')+'</p>'
      +(data.build_summary?'<p class="note">'+escapeHtml(data.build_summary)+'</p>':'');
    return;
  }

  var appIdea=(data.normalized_request||{}).app_idea||'Untitled project';
  var title=appIdea.length>60?appIdea.slice(0,57)+'...':appIdea;
  icon.textContent=(title.trim().charAt(0)||'?').toUpperCase();
  document.getElementById('detailName').textContent=title;
  document.getElementById('detailMeta').textContent='v'+data.version+' · '+data.approval_status;
  sowBox.style.display='block';
  document.getElementById('detailSow').textContent=data.scope_of_work_markdown||'No scope drafted yet.';
  document.getElementById('detailDeleteBtn').style.display='inline-block';
  document.getElementById('detailAmendBox').style.display='block';

  renderPreview(null, 'There is no live deployment URL wired up for this build pipeline yet — this project only tracks build/generation status.');
  // This pipeline never has a live preview (see message above), so Preview is a dead
  // end here - default straight to Details, where approve/build actions and their
  // status actually render, instead of leaving the user looking at a static message
  // with no sign that anything happened after they click a button.
  showDetailTab('details');

  if(data.approval_status!=='scope_approved'){
    var approveBtn=document.createElement('button');
    approveBtn.className='primary';approveBtn.textContent='Approve scope';
    approveBtn.onclick=function(){approveProject(data.scoping_request_id, approveBtn)};
    actions.appendChild(approveBtn);
  }else if(!data.build){
    var buildBtn=document.createElement('button');
    buildBtn.className='primary';buildBtn.textContent='Start build';
    buildBtn.onclick=function(){buildProject(data.scoping_request_id, buildBtn)};
    actions.appendChild(buildBtn);
  }else{
    buildStatus.innerHTML=renderBuildStatus(data.build);
  }
}

function stepIcon(status){
  if(status==='completed')return '✓';
  if(status==='failed')return '✗';
  if(status==='blocked')return '⚠';
  return '•';
}

function formatDuration(ms){
  var totalSeconds=Math.max(0,Math.round(ms/1000));
  var minutes=Math.floor(totalSeconds/60);
  var seconds=totalSeconds%60;
  return minutes>0?(minutes+'m '+seconds+'s'):(seconds+'s');
}

function renderBuildStatus(build){
  var stepCount=build.step_count||0;
  var completedCount=build.completed_step_count||0;
  var progress=stepCount?Math.round(100*completedCount/stepCount):0;
  var statusLabel=humanizeStatus(build.status||'unknown');
  var html='<p class="stage-label">'+escapeHtml(statusLabel)+' &middot; '+completedCount+'/'+stepCount+' steps';
  if(build.failed_step_count){html+=' &middot; '+build.failed_step_count+' failed'}
  html+='</p>';
  html+='<div class="progress-track"><div class="progress-fill" style="width:'+progress+'%"></div></div>';
  if(build.created_at&&build.completed_at){
    var durationMs=new Date(build.completed_at).getTime()-new Date(build.created_at).getTime();
    html+='<p class="note">Built in '+formatDuration(durationMs)+'.</p>';
  }
  var steps=build.steps||[];
  if(steps.length){
    html+='<div class="step-list">'+steps.map(function(step){
      return '<div class="step-row step-'+escapeHtml(step.status||'pending')+'">'
        +'<span class="step-icon">'+stepIcon(step.status)+'</span>'
        +'<span>'+escapeHtml(step.title||step.status||'Step')+'</span></div>';
    }).join('')+'</div>';
  }
  html+='<p class="note">No live deployment URL is wired up for customer builds yet — this reflects build/generation status only.</p>';
  return html;
}

window.approveProject=async function(scopingRequestId, btn){
  document.getElementById('detailError').textContent='';
  showDetailTab('details');
  if(btn){btn.disabled=true;btn.textContent='Approving…'}
  document.getElementById('detailBuildStatus').innerHTML='<p class="note">Approving…</p>';
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(scopingRequestId)+'/approve',{method:'POST',headers:authHeaders()});
    var data=await response.json();
    if(!response.ok||!data.success){document.getElementById('detailError').textContent=data.detail||'Could not approve.';if(btn){btn.disabled=false;btn.textContent='Approve scope'}return}
    refreshProjects();
    openProjectDetail(scopingRequestId);
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error;if(btn){btn.disabled=false;btn.textContent='Approve scope'}}
};

window.buildProject=async function(scopingRequestId, btn){
  document.getElementById('detailError').textContent='';
  showDetailTab('details');
  if(btn){btn.disabled=true;btn.textContent='Building…'}
  // The build call blocks until the real planning/engineering/generation pipeline
  // finishes - there's no live "step 3 of 5" signal to poll for mid-request, so the
  // most honest thing this can show while waiting is that it's still alive: a
  // ticking clock, not a fake progress bar implying visibility we don't have.
  var startedAt=Date.now();
  var buildStatusBox=document.getElementById('detailBuildStatus');
  var tick=function(){
    buildStatusBox.innerHTML='<p class="note">Building… this runs the real planning/engineering/generation pipeline and can take a little while.</p>'
      +'<p class="note elapsed-clock">'+formatDuration(Date.now()-startedAt)+' elapsed</p>';
  };
  tick();
  var timer=setInterval(tick,1000);
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(scopingRequestId)+'/build',{method:'POST',headers:authHeaders(),body:JSON.stringify({})});
    var data=await response.json();
    if(!data.success){document.getElementById('detailError').textContent=data.reason||data.detail||'Build failed to start.';if(btn){btn.disabled=false;btn.textContent='Start build'}}
    refreshProjects();
    openProjectDetail(scopingRequestId);
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error;if(btn){btn.disabled=false;btn.textContent='Start build'}}
  finally{clearInterval(timer)}
};

window.submitAmend=async function(){
  var err=document.getElementById('detailError');err.textContent='';
  var input=document.getElementById('amendInput');
  var changeRequest=input.value.trim();
  if(!changeRequest){err.textContent='Describe what to change first.';return}
  var btn=document.getElementById('amendSendBtn');
  btn.disabled=true;
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(currentDetailId)+'/amend',{method:'POST',headers:authHeaders(),body:JSON.stringify({app_request:changeRequest})});
    var data=await response.json();
    if(!response.ok||!data.success){err.textContent=data.message||data.detail||'Could not update the scope.';return}
    refreshProjects();
    openProjectDetail(data.scoping_request_id);
  }catch(error){err.textContent='Request failed: '+error}
  finally{btn.disabled=false}
};

window.deleteProject=async function(){
  if(!confirm('Delete this project? This removes it and every earlier version. This cannot be undone.'))return;
  document.getElementById('detailError').textContent='';
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(currentDetailId),{method:'DELETE',headers:authHeaders()});
    var data=await response.json();
    if(!response.ok||!data.success){document.getElementById('detailError').textContent=data.detail||'Could not delete project.';return}
    refreshProjects();
    closeProjectDetail();
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
