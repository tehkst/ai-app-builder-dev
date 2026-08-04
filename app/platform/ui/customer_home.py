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
.view.wide{max-width:1240px}

h1.hero{font-size:30px;letter-spacing:-.03em;text-align:center;margin:0 0 22px}
.composer{background:white;border:1px solid #eadfd5;border-radius:20px;padding:16px 18px;box-shadow:0 18px 60px rgba(30,26,23,.06)}
.composer textarea{width:100%;border:0;outline:0;resize:none;font:inherit;font-size:15px;min-height:52px;background:transparent}
.composer-row{display:flex;align-items:center;gap:10px;margin-top:6px}
.icon-btn{width:34px;height:34px;border-radius:10px;border:1px solid #eadfd5;background:#faf6f1;color:#686b75;display:inline-flex;align-items:center;justify-content:center;font-size:16px}
.icon-btn:hover{background:#f1e9df}
.icon-btn.listening{background:#fdecec;color:#c93b3b;border-color:#f1c9c9;animation:pulse 1.1s ease-in-out infinite}
.icon-btn[disabled]{cursor:not-allowed;opacity:.5}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(201,59,59,.35)}50%{box-shadow:0 0 0 6px rgba(201,59,59,0)}}
.spacer{flex:1}
.send-btn{width:36px;height:36px;border-radius:999px;border:0;background:#2b6df6;color:white;font-size:16px;display:inline-flex;align-items:center;justify-content:center}
.send-btn:disabled{background:#c9d8f8;cursor:not-allowed}

.attach-row{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}
.attach-chip{display:inline-flex;align-items:center;gap:6px;background:#eaf1fe;color:#2b6df6;border-radius:999px;padding:4px 6px 4px 12px;font-size:12px;font-weight:700;max-width:220px}
.attach-chip span.name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.attach-chip button{border:0;background:none;color:inherit;font-weight:900;cursor:pointer;padding:2px 6px;font-size:13px;border-radius:999px}
.attach-chip button:hover{background:rgba(43,109,246,.15)}
.voice-note{text-align:center;color:#8a8d98;font-size:12.5px;margin-top:8px;min-height:16px}

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
button.secondary{border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:12px;padding:12px 18px;font-weight:800}
button.danger{border:1px solid #f1c9c9;background:#fff5f5;color:#c93b3b;border-radius:10px;padding:7px 12px;font-weight:700;font-size:12.5px}
.error{color:#cf3d3d;font-size:13px;margin-top:10px;min-height:18px}
.note{font-size:13px;margin-top:10px;color:#8a8d98}
.warn-banner{background:#fff7e6;border:1px solid #f2d999;color:#8a5a00;border-radius:12px;padding:12px 14px;font-size:13px;margin-bottom:14px}
.secret-name{font-weight:700}
.secret-meta{font-size:12px;color:#8a8d98}

.sow{white-space:pre-wrap;font-size:13px;background:#faf6f1;border:1px solid #eadfd5;border-radius:12px;padding:14px;max-height:320px;overflow:auto;margin-top:10px}

.workspace-top{display:flex;align-items:center;gap:14px;margin-bottom:18px}
.back-btn{border:1px solid #eadfd5;background:white;color:#55585f;border-radius:10px;padding:8px 14px;font-weight:700;font-size:13px}
.workspace-top-text{flex:1;min-width:0}
.workspace-top-text h1{font-size:20px;margin:0 0 4px;letter-spacing:-.02em}
.workspace-top .proj-icon{width:40px;height:40px;font-size:16px}

.workspace-split{display:flex;align-items:stretch;gap:26px;min-height:64vh}
.workspace-left{width:380px;flex:0 0 380px;display:flex;flex-direction:column;gap:14px;min-width:0}
.workspace-right{flex:1;min-width:0;display:flex;flex-direction:column}
.workspace-right-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.workspace-right-top h2{margin:0}
.publish-btn{border:0;border-radius:10px;padding:9px 16px;font-weight:800;font-size:13px;background:#2b6df6;color:white}
.publish-btn:disabled{background:#c9d8f8;cursor:not-allowed}
.open-live-btn{border:1px solid #eadfd5;background:white;color:#55585f;border-radius:10px;padding:9px 14px;font-weight:700;font-size:13px;display:none}

.preview-frame-wrap{border:1px solid #eadfd5;border-radius:16px;overflow:hidden;background:white;box-shadow:0 18px 60px rgba(30,26,23,.06);flex:1;display:flex}
.preview-frame-wrap iframe{width:100%;flex:1;border:0;display:block;min-height:520px}
.preview-empty{text-align:center;padding:60px 20px;color:#8a8d98;background:white;border:1px solid #eadfd5;border-radius:16px;flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center}
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
.step-escalated .step-icon{background:#fff3d6;color:#b8790a}
.step-running .step-icon{background:#e8f0fe;color:#2b6df6}
.step-reason{margin:0 0 4px 28px;font-size:12px;color:#a34a4a}
.step-completed,.step-failed,.step-escalated{color:#2b2d33}
.decision-panel{background:#fff9ee;border:1px solid #f2d999;border-radius:14px;padding:14px;margin-top:10px}
.decision-panel h4{margin:0 0 8px;font-size:12px;color:#8a5a00;text-transform:uppercase;letter-spacing:.04em}
.decision-concerns{margin:8px 0;padding-left:18px;font-size:13px;color:#55585f}
.decision-redirect{font-size:13px;color:#55585f;margin:8px 0}
.decision-actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.decision-actions button{padding:9px 14px;font-size:13px}
.elapsed-clock{font-variant-numeric:tabular-nums;font-weight:700}
.left-scroll{flex:1;overflow:auto;padding-right:2px}
.left-card{background:white;border:1px solid #eadfd5;border-radius:16px;padding:16px;margin-bottom:12px}
.left-card h3{font-size:13px;margin:0 0 8px;color:#55585f;text-transform:uppercase;letter-spacing:.04em}

@media (max-width:900px){
  .workspace-split{flex-direction:column}
  .workspace-left{width:100%;flex:none}
}
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
<div class="attach-row" id="composerAttachRow" style="display:none"></div>
<textarea id="composerInput" rows="2" placeholder="Describe the app you want to build..."></textarea>
<div class="composer-row">
<button class="icon-btn" id="composerAttachBtn" title="Attach a reference file">+</button>
<input type="file" id="composerFileInput" multiple style="display:none" accept=".txt,.md,.csv,.json,.pdf,image/*,text/*"/>
<button class="icon-btn" id="composerVoiceBtn" title="Dictate with your microphone">&#127908;</button>
<div class="spacer"></div>
<button class="send-btn" id="composerSendBtn" onclick="submitComposer()">&#8593;</button>
</div>
</div>
<p class="voice-note" id="voiceNote"></p>
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
<p class="muted">Projects whose build has completed. Requesting publish sends the build to a founder for review before it goes live - there's no automated, unreviewed path to a public URL.</p>
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


<section class="view wide" id="view-project">
<div class="workspace-top">
<button class="back-btn" onclick="closeProjectDetail()">&larr; Back</button>
<div class="proj-icon" id="detailIcon">?</div>
<div class="workspace-top-text">
<h1 id="detailName">Project</h1>
<p class="muted" id="detailMeta"></p>
</div>
<button id="detailDeleteBtn" class="danger" style="display:none" onclick="deleteProject()">Delete</button>
</div>
<div id="detailError" class="error"></div>

<div class="workspace-split">
<div class="workspace-left">
<div class="left-scroll" id="leftScroll">
<div class="left-card" id="detailActionsCard">
<h3>Scope of work</h3>
<div id="detailSow" class="sow">No scope drafted yet.</div>
<div id="detailActions" class="actions"></div>
<div id="detailBuildStatus"></div>
</div>
<div class="left-card" id="detailAmendBox" style="display:none">
<h3>Request a change</h3>
<textarea class="field" id="amendInput" rows="2" placeholder="Describe what to change about this scope..."></textarea>
<div class="attach-row" id="amendAttachRow" style="display:none"></div>
<div class="actions">
<button class="icon-btn" id="amendAttachBtn" title="Attach a reference file">+</button>
<input type="file" id="amendFileInput" multiple style="display:none" accept=".txt,.md,.csv,.json,.pdf,image/*,text/*"/>
<button class="primary" id="amendSendBtn" onclick="submitAmend()">Send</button>
</div>
</div>
<div class="left-card" id="detailFixBox" style="display:none">
<h3>Report an issue</h3>
<p class="note">Found something broken? Describe it and we'll fix it and add a test so it doesn't come back.</p>
<textarea class="field" id="fixInput" rows="2" placeholder="Describe what's broken..."></textarea>
<div class="actions"><button class="primary" id="fixSendBtn" onclick="submitFix()">Send</button></div>
<div id="fixResult" class="note"></div>
</div>
</div>
</div>

<div class="workspace-right">
<div class="workspace-right-top">
<h2>Preview</h2>
<div class="actions" style="margin-top:0">
<a id="detailOpenLive" class="open-live-btn" href="#" target="_blank" rel="noopener">Open in new tab &rarr;</a>
<button id="publishBtn" class="publish-btn" style="display:none" onclick="requestPublish()">Request publish</button>
</div>
</div>
<div id="detailPreview"><p class="empty">Loading…</p></div>
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

// ---- attachments (shared helper used by both the home composer and the amend box) ----
var TEXT_MIME_HINT=/^text\\/|json|csv|markdown/i;
var MAX_ATTACHMENTS=5;

function makeAttachmentController(fileInputId, rowId){
  var fileInput=document.getElementById(fileInputId);
  var row=document.getElementById(rowId);
  var items=[];

  function render(){
    row.style.display=items.length?'flex':'none';
    row.innerHTML='';
    items.forEach(function(item,index){
      var chip=document.createElement('span');
      chip.className='attach-chip';
      chip.innerHTML='<span class="name">'+escapeHtml(item.name)+'</span>';
      var removeBtn=document.createElement('button');
      removeBtn.type='button';removeBtn.textContent='\\u00d7';
      removeBtn.onclick=function(){items.splice(index,1);render()};
      chip.appendChild(removeBtn);
      row.appendChild(chip);
    });
  }

  function readFile(file){
    return new Promise(function(resolve){
      var isTextish=TEXT_MIME_HINT.test(file.type)||/\\.(txt|md|csv|json)$/i.test(file.name);
      if(!isTextish){resolve({name:file.name,mime_type:file.type||null,text_content:null});return}
      var reader=new FileReader();
      reader.onload=function(){resolve({name:file.name,mime_type:file.type||null,text_content:String(reader.result||'')})};
      reader.onerror=function(){resolve({name:file.name,mime_type:file.type||null,text_content:null})};
      reader.readAsText(file);
    });
  }

  fileInput.addEventListener('change',function(){
    var files=Array.from(fileInput.files||[]).slice(0,MAX_ATTACHMENTS-items.length);
    Promise.all(files.map(readFile)).then(function(results){
      items=items.concat(results).slice(0,MAX_ATTACHMENTS);
      render();
    });
    fileInput.value='';
  });

  return {
    list:function(){return items},
    clear:function(){items=[];render()}
  };
}

var composerAttachments=makeAttachmentController('composerFileInput','composerAttachRow');
document.getElementById('composerAttachBtn').addEventListener('click',function(){document.getElementById('composerFileInput').click()});

// ---- voice input (Web Speech API - client-side only, best-effort by browser) ----
function makeVoiceController(button, textarea, noteEl){
  var Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Recognition){
    button.addEventListener('click',function(){
      if(noteEl)noteEl.textContent='Voice input is not supported in this browser.';
    });
    return;
  }
  var recognizer=new Recognition();
  recognizer.continuous=true;
  recognizer.interimResults=false;
  recognizer.lang=(navigator.language||'en-US');
  var listening=false;

  recognizer.onresult=function(event){
    var transcript='';
    for(var i=event.resultIndex;i<event.results.length;i++){
      if(event.results[i].isFinal)transcript+=event.results[i][0].transcript;
    }
    if(transcript.trim()){
      textarea.value=(textarea.value?textarea.value.trim()+' ':'')+transcript.trim();
    }
  };
  recognizer.onerror=function(event){
    listening=false;button.classList.remove('listening');
    if(noteEl)noteEl.textContent='Voice input stopped: '+(event.error||'unknown error');
  };
  recognizer.onend=function(){
    listening=false;button.classList.remove('listening');
  };
  button.addEventListener('click',function(){
    if(listening){recognizer.stop();return}
    try{
      recognizer.start();
      listening=true;button.classList.add('listening');
      if(noteEl)noteEl.textContent='Listening… click the microphone again to stop.';
    }catch(error){
      if(noteEl)noteEl.textContent='Could not start voice input: '+error;
    }
  });
}
makeVoiceController(document.getElementById('composerVoiceBtn'),document.getElementById('composerInput'),document.getElementById('voiceNote'));

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
    var response=await fetch('/api/projects/draft-scope',{method:'POST',headers:authHeaders(),body:JSON.stringify({app_request:idea,attachments:composerAttachments.list()})});
    var data=await response.json();
    if(!response.ok||!data.success){err.textContent=data.message||data.detail||'Could not draft a scope.';return}
    input.value='';
    composerAttachments.clear();
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
    if(build.status==='escalated'){return {text:'Needs your decision',cls:'tag-bad'}}
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
var currentDetailSource=null;
var amendAttachments=makeAttachmentController('amendFileInput','amendAttachRow');
document.getElementById('amendAttachBtn').addEventListener('click',function(){document.getElementById('amendFileInput').click()});

window.closeProjectDetail=function(){showSection(previousSection)};

window.openProjectDetail=async function(scopingRequestId){
  previousSection=Array.from(document.querySelectorAll('.view.active')).map(function(el){return el.id.replace('view-','')})[0]||'home';
  currentDetailId=scopingRequestId;
  document.getElementById('detailError').textContent='';
  document.getElementById('detailPreview').innerHTML='<p class="empty">Loading…</p>';
  document.getElementById('detailActions').innerHTML='';
  document.getElementById('detailBuildStatus').innerHTML='';
  document.getElementById('detailOpenLive').style.display='none';
  document.getElementById('publishBtn').style.display='none';
  document.getElementById('detailDeleteBtn').style.display='none';
  document.getElementById('detailAmendBox').style.display='none';
  document.getElementById('amendInput').value='';
  amendAttachments.clear();
  document.getElementById('detailFixBox').style.display='none';
  document.getElementById('fixInput').value='';
  document.getElementById('fixResult').textContent='';
  document.getElementById('detailName').textContent='Loading…';
  document.getElementById('detailMeta').textContent='';
  showSection('project');
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(scopingRequestId),{headers:authHeaders()});
    var data=await response.json();
    if(!response.ok||!data.success){document.getElementById('detailError').textContent=data.detail||'Could not load project.';return}
    currentDetailSource=data.source;
    renderProjectDetail(data);
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error}
};

function renderPreview(options){
  var box=document.getElementById('detailPreview');
  var openLive=document.getElementById('detailOpenLive');
  if(options.liveUrl){
    box.innerHTML='<div class="preview-frame-wrap"><iframe src="'+escapeHtml(options.liveUrl)+'" title="Live app preview"></iframe></div>';
    openLive.href=options.liveUrl;
    openLive.textContent='Open live app \\u2192';
    openLive.style.display='inline-block';
  }else if(options.previewUrl){
    box.innerHTML='<div class="preview-frame-wrap"><iframe src="'+escapeHtml(options.previewUrl)+'" title="Generated app preview"></iframe></div>';
    openLive.href=options.previewUrl;
    openLive.textContent='Open preview in new tab \\u2192';
    openLive.style.display='inline-block';
  }else{
    box.innerHTML='<div class="preview-empty"><p class="big">No preview yet</p><p>'+escapeHtml(options.emptyMessage||'')+'</p></div>';
  }
}

function renderPublishControl(data){
  var publishBtn=document.getElementById('publishBtn');
  var buildCompleted=data.build&&data.build.status==='completed';
  if(!buildCompleted){publishBtn.style.display='none';return}
  publishBtn.style.display='inline-flex';
  var status=data.publish_status;
  if(status==='live'){
    publishBtn.disabled=true;
    publishBtn.textContent='Published \\u2014 live';
  }else if(status==='pr_created'){
    publishBtn.disabled=true;
    publishBtn.textContent='Approved \\u2014 in final review before launch';
  }else if(status==='approved'){
    publishBtn.disabled=true;
    publishBtn.textContent='Approved \\u2014 preparing for launch';
  }else if(status==='requested'){
    publishBtn.disabled=true;
    publishBtn.textContent='Publish requested \\u2014 awaiting review';
  }else if(status==='rejected'){
    publishBtn.disabled=false;
    publishBtn.textContent='Publish request declined \\u2014 request again';
  }else{
    publishBtn.disabled=false;
    publishBtn.textContent='Request publish';
  }
}

window.requestPublish=async function(){
  var publishBtn=document.getElementById('publishBtn');
  publishBtn.disabled=true;publishBtn.textContent='Requesting…';
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(currentDetailId)+'/request-publish',{method:'POST',headers:authHeaders()});
    var data=await response.json();
    if(!response.ok||!data.success){document.getElementById('detailError').textContent=data.status||data.detail||'Could not request publish.';publishBtn.disabled=false;publishBtn.textContent='Request publish';return}
    publishBtn.disabled=true;
    publishBtn.textContent='Publish requested \\u2014 awaiting review';
  }catch(error){document.getElementById('detailError').textContent='Request failed: '+error;publishBtn.disabled=false;publishBtn.textContent='Request publish'}
};

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
    sowBox.textContent='Not applicable for this build pipeline.';

    renderPreview({liveUrl:data.live_url,emptyMessage:data.message||'This application has not been deployed to a live URL yet.'});

    var progress=typeof data.progress==='number'?data.progress:0;
    buildStatus.innerHTML='<p class="stage-label">'+escapeHtml(humanizeStatus(data.mission_stage||data.status))+'</p>'
      +'<div class="progress-track"><div class="progress-fill" style="width:'+progress+'%"></div></div>'
      +'<p class="note">'+escapeHtml(data.message||'')+'</p>'
      +(data.build_summary?'<p class="note">'+escapeHtml(data.build_summary)+'</p>':'');
    document.getElementById('detailDeleteBtn').style.display='inline-block';
    return;
  }

  var appIdea=(data.normalized_request||{}).app_idea||'Untitled project';
  var title=appIdea.length>60?appIdea.slice(0,57)+'...':appIdea;
  icon.textContent=(title.trim().charAt(0)||'?').toUpperCase();
  document.getElementById('detailName').textContent=title;
  document.getElementById('detailMeta').textContent='v'+data.version+' · '+data.approval_status;
  sowBox.textContent=data.scope_of_work_markdown||'No scope drafted yet.';
  document.getElementById('detailDeleteBtn').style.display='inline-block';
  document.getElementById('detailAmendBox').style.display='block';

  var buildCompleted=data.build&&data.build.status==='completed';
  if(data.publish_status==='live'&&data.live_url){
    renderPreview({liveUrl:data.live_url});
  }else if(buildCompleted){
    var previewUrl='/api/projects/'+encodeURIComponent(data.scoping_request_id)+'/preview.html?token='+encodeURIComponent(token);
    renderPreview({previewUrl:previewUrl});
  }else{
    renderPreview({emptyMessage:'A preview becomes available once this build finishes.'});
  }
  renderPublishControl(data);

  if(data.approval_status!=='scope_approved'){
    var editBtn=document.createElement('button');
    editBtn.className='secondary';editBtn.textContent='Edit scope';
    editBtn.onclick=function(){
      document.getElementById('detailAmendBox').style.display='block';
      var amendInput=document.getElementById('amendInput');
      amendInput.scrollIntoView({behavior:'smooth',block:'center'});
      amendInput.focus();
    };
    actions.appendChild(editBtn);
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
    if(data.build.status==='completed'){
      document.getElementById('detailFixBox').style.display='block';
    }else if(data.build.status==='escalated'){
      var escalatedStep=(data.build.steps||[]).filter(function(s){return s.status==='escalated'})[0];
      if(escalatedStep){buildStatus.appendChild(renderDecisionPanel(data.scoping_request_id, escalatedStep))}
    }else if(data.build.status==='failed'||data.build.status==='blocked'){
      var retryBtn=document.createElement('button');
      retryBtn.className='primary';retryBtn.textContent='Retry build';
      retryBtn.onclick=function(){buildProject(data.scoping_request_id, retryBtn)};
      actions.appendChild(retryBtn);
    }
  }
}

function renderDecisionPanel(scopingRequestId, step){
  // A management agent's real escalate/unresolved-redirect decision, surfaced with
  // real Approve/Reject actions - not the old dead-end "red X, no recourse" state.
  var decision=step.decision||{};
  var panel=document.createElement('div');
  panel.className='decision-panel';
  var html='<h4>Founder decision needed</h4>';
  html+='<p class="note">'+escapeHtml(decision.rationale||step.message||'This step needs your review before the build can continue.')+'</p>';
  if(decision.concerns&&decision.concerns.length){
    html+='<ul class="decision-concerns">'+decision.concerns.map(function(c){return '<li>'+escapeHtml(c)+'</li>'}).join('')+'</ul>';
  }
  if(decision.redirect_instructions){
    html+='<p class="decision-redirect"><strong>Suggested change:</strong> '+escapeHtml(decision.redirect_instructions)+'</p>';
  }
  panel.innerHTML=html;
  var actionsRow=document.createElement('div');
  actionsRow.className='decision-actions';
  var approveBtn=document.createElement('button');
  approveBtn.className='primary';approveBtn.textContent='Approve & continue';
  approveBtn.onclick=function(){submitStepDecision(scopingRequestId, step.step_run_id, 'approve')};
  var editBtn=document.createElement('button');
  editBtn.className='secondary';editBtn.textContent='Edit scope instead';
  editBtn.onclick=function(){
    document.getElementById('detailAmendBox').style.display='block';
    var amendInput=document.getElementById('amendInput');
    amendInput.scrollIntoView({behavior:'smooth',block:'center'});
    amendInput.focus();
  };
  var rejectBtn=document.createElement('button');
  rejectBtn.className='danger';rejectBtn.textContent='Reject';
  rejectBtn.onclick=function(){submitStepDecision(scopingRequestId, step.step_run_id, 'reject')};
  actionsRow.appendChild(approveBtn);
  actionsRow.appendChild(editBtn);
  actionsRow.appendChild(rejectBtn);
  panel.appendChild(actionsRow);
  return panel;
}

function stepIcon(status){
  if(status==='completed')return '✓';
  if(status==='failed')return '✗';
  if(status==='blocked')return '⚠';
  if(status==='escalated')return '⏸';
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
        +'<span>'+escapeHtml(step.title||step.status||'Step')+'</span></div>'
        +(step.message?'<p class="note step-reason">'+escapeHtml(step.message)+'</p>':'');
    }).join('')+'</div>';
  }
  return html;
}

window.approveProject=async function(scopingRequestId, btn){
  document.getElementById('detailError').textContent='';
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

// Shared by buildProject and submitStepDecision - both run a real pipeline stage in
// a background thread server-side and relay execute_agent_workflow's
// on_step_complete callback as SSE events, so the founder watches each agent's
// actual decision the moment it finishes. One streaming mechanism, not a separate
// one per action.
function streamBuildEvents(url, body, startingLabel){
  var startedAt=Date.now();
  var buildStatusBox=document.getElementById('detailBuildStatus');
  var stepsSoFar=[];
  function renderLive(){
    var html='<p class="note">'+startingLabel+' '+formatDuration(Date.now()-startedAt)+' elapsed.</p>';
    if(stepsSoFar.length){
      html+='<div class="step-list">'+stepsSoFar.map(function(step){
        return '<div class="step-row step-'+escapeHtml(step.status||'running')+'">'
          +'<span class="step-icon">'+stepIcon(step.status)+'</span>'
          +'<span>'+escapeHtml(step.title||step.step_id||'Step')+'</span></div>'
          +(step.message?'<p class="note step-reason">'+escapeHtml(step.message)+'</p>':'');
      }).join('')+'</div>';
    }
    buildStatusBox.innerHTML=html;
  }
  function upsertStep(stepId, patch){
    var existing=stepsSoFar.filter(function(s){return s.step_id===stepId})[0];
    if(existing){Object.assign(existing,patch)}else{stepsSoFar.push(Object.assign({step_id:stepId},patch))}
    renderLive();
  }
  var tick=setInterval(renderLive,1000);
  renderLive();
  var failed=false;
  return (async function(){
    try{
      var response=await fetch(url,{method:'POST',headers:authHeaders(),body:JSON.stringify(body||{})});
      if(!response.ok||!response.body){throw new Error('Stream request failed with status '+response.status)}
      var reader=response.body.getReader();
      var decoder=new TextDecoder();
      var buffer='';
      var done=false;
      while(!done){
        var chunk=await reader.read();
        if(chunk.done)break;
        buffer+=decoder.decode(chunk.value,{stream:true});
        var parts=buffer.split('\\n\\n');
        buffer=parts.pop();
        for(var i=0;i<parts.length;i++){
          var line=parts[i];
          if(line.indexOf('data: ')!==0)continue;
          var event;
          try{event=JSON.parse(line.slice(6))}catch(parseError){continue}
          if(event.type==='step_started'){
            upsertStep(event.step_id,{title:event.title,status:'running'});
          }else if(event.type==='step_completed'){
            upsertStep(event.step_id,{title:event.title,status:event.status,message:event.message});
          }else if(event.type==='workflow_completed'){
            var status=event.result&&event.result.status;
            if(!(event.result&&event.result.success)&&status!=='escalated'){
              document.getElementById('detailError').textContent=(event.result&&(event.result.reason||status))||'Build did not complete successfully.';
            }
            done=true;
          }else if(event.type==='error'){
            document.getElementById('detailError').textContent=event.error||'Build failed.';
            failed=true;
            done=true;
          }
        }
      }
    }catch(error){
      document.getElementById('detailError').textContent='Request failed: '+error;
      failed=true;
    }finally{clearInterval(tick)}
    return failed;
  })();
}

window.buildProject=async function(scopingRequestId, btn){
  document.getElementById('detailError').textContent='';
  if(btn){btn.disabled=true;btn.textContent='Building…'}
  var buildFailedToStart=await streamBuildEvents(
    '/api/projects/'+encodeURIComponent(scopingRequestId)+'/build/stream', {}, 'Building…'
  );
  if(buildFailedToStart&&btn){btn.disabled=false;btn.textContent='Start build'}
  refreshProjects();
  openProjectDetail(scopingRequestId);
};

window.submitStepDecision=async function(scopingRequestId, stepRunId, action){
  if(action==='reject'&&!confirm('Reject this step? The build stops here - this cannot be undone.'))return;
  document.getElementById('detailError').textContent='';
  var note=action==='reject'?(prompt('Optional note for rejecting this step:')||null):null;
  Array.from(document.querySelectorAll('.decision-actions button')).forEach(function(b){b.disabled=true});
  var url='/api/projects/'+encodeURIComponent(scopingRequestId)+'/steps/'+encodeURIComponent(stepRunId)+'/decision/stream';
  await streamBuildEvents(url, {action:action, note:note}, action==='approve'?'Resuming build…':'Stopping build…');
  refreshProjects();
  openProjectDetail(scopingRequestId);
};

window.submitAmend=async function(){
  var err=document.getElementById('detailError');err.textContent='';
  var input=document.getElementById('amendInput');
  var changeRequest=input.value.trim();
  if(!changeRequest){err.textContent='Describe what to change first.';return}
  var btn=document.getElementById('amendSendBtn');
  btn.disabled=true;
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(currentDetailId)+'/amend',{method:'POST',headers:authHeaders(),body:JSON.stringify({app_request:changeRequest,attachments:amendAttachments.list()})});
    var data=await response.json();
    if(!response.ok||!data.success){err.textContent=data.message||data.detail||'Could not update the scope.';return}
    amendAttachments.clear();
    refreshProjects();
    openProjectDetail(data.scoping_request_id);
  }catch(error){err.textContent='Request failed: '+error}
  finally{btn.disabled=false}
};

window.submitFix=async function(){
  var err=document.getElementById('detailError');err.textContent='';
  var resultBox=document.getElementById('fixResult');resultBox.textContent='';
  var input=document.getElementById('fixInput');
  var bugReport=input.value.trim();
  if(!bugReport){err.textContent='Describe what\\'s broken first.';return}
  var btn=document.getElementById('fixSendBtn');
  btn.disabled=true;btn.textContent='Fixing…';
  resultBox.textContent='Reproducing and fixing the reported issue - this can take a little while.';
  try{
    var response=await fetch('/api/projects/'+encodeURIComponent(currentDetailId)+'/fix',{method:'POST',headers:authHeaders(),body:JSON.stringify({bug_report:bugReport})});
    var data=await response.json();
    if(!response.ok||!data.success){resultBox.textContent=data.blocked_reason||data.detail||'Could not fix that issue.';return}
    input.value='';
    resultBox.textContent='Fixed '+(data.fixed_file_count||0)+' file(s) and added a regression test ('+((data.regression_test_paths||[])[0]||'test added')+').';
    openProjectDetail(currentDetailId);
  }catch(error){resultBox.textContent='Request failed: '+error}
  finally{btn.disabled=false;btn.textContent='Send'}
};

window.deleteProject=async function(){
  if(currentDetailSource==='saas_builder'){
    if(!confirm('Permanently delete this live app? This deletes the deployed application and all its data. This cannot be undone.'))return;
    document.getElementById('detailError').textContent='';
    try{
      var resp=await fetch('/api/saas-builder/builds/'+encodeURIComponent(currentDetailId),{method:'DELETE',headers:authHeaders()});
      var result=await resp.json();
      if(!resp.ok||result.status!=='deleted'){document.getElementById('detailError').textContent=result.detail||result.status||'Could not delete this app.';return}
      refreshProjects();
      closeProjectDetail();
    }catch(error){document.getElementById('detailError').textContent='Request failed: '+error}
    return;
  }
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
