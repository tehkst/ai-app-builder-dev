"""Mission Control view for Orca missions.

Adds an "Orca Missions" nav item and section to the founder dashboard at load time (same
pattern as the mission pipeline and publish review panels). Talks only to the founder-only
`/mission-control/orca/*` endpoints with the Mission Control session token, and escapes every
piece of text that comes from a mission (goals, AI employee output, check logs).
"""
from __future__ import annotations

import json

ORCA_SECTION_HTML = r"""
<div class="card hero"><h2>Orca Missions</h2>
<p>Tell your AI team what to change in an app, in plain words. They plan it, build it, check it and
show you their work. You stay in charge: nothing runs without your OK, and nothing is merged or
deployed from here.</p></div>
<div class="grid orca-intro">
  <div class="card"><h2>How it works</h2>
    <ol class="orca-steps">
      <li><strong>You give a goal</strong> and pick the app (workspace) to work on.</li>
      <li><strong>The architect plans it</strong> as a few small tasks, each with a check that proves it's done.</li>
      <li><strong>You decide</strong> whether the team may run the app's tests while they work.</li>
      <li><strong>The team builds each task</strong>: a builder makes the change, QA checks it works, and for
        anything people see the UX Designer checks it's clear and accessible. A task gets up to 3 tries;
        if it still fails, it comes back to you with the full story.</li>
    </ol>
  </div>
  <div class="card"><h2>Your AI team</h2><div id="orcaTeam" class="orca-team"><p class="muted">Loading...</p></div></div>
  <div class="card"><h2>Try a goal</h2>
    <p class="muted">Click one to fill in the form below, then edit it to suit.</p>
    <div class="orca-examples">
      <button class="secondary orca-example">Add a GET /health endpoint that returns {"status": "ok"}, with a test.</button>
      <button class="secondary orca-example">Add a contact page with a name, email and message form that validates input and shows a thank-you message, with a test.</button>
      <button class="secondary orca-example">Make the home page usable on a phone: readable text, no sideways scrolling, and a working menu.</button>
    </div>
  </div>
</div>
<div class="layout">
  <div class="card"><h2>Missions</h2>
    <div class="actions"><button class="secondary" id="orcaRefreshBtn">Refresh</button></div>
    <div id="orcaMissionList" class="orca-list"><p class="muted">Loading...</p></div>
  </div>
  <div class="card"><h2>New mission</h2>
    <label for="orcaGoal">Goal</label>
    <textarea id="orcaGoal" rows="4" placeholder="Example: Add a GET /health endpoint that returns {&quot;status&quot;: &quot;ok&quot;}, with a test."></textarea>
    <label for="orcaWorkspace">Workspace</label>
    <select id="orcaWorkspace"><option value="">Loading workspaces...</option></select>
    <label class="orca-check"><input type="checkbox" id="orcaApproveExec"> Allow Orca to run this app's tests
      (test runners and read-only commands only). You can also decide after seeing the plan.</label>
    <div class="actions"><button class="primary" id="orcaStartBtn">Start mission</button></div>
    <p id="orcaStartMsg" class="muted"></p>
  </div>
</div>
<div class="card"><h2>Mission detail</h2><div id="orcaMissionDetail"><p class="muted">Select a mission.</p></div></div>
<style>
.orca-list{display:grid;gap:8px;margin-top:12px}
.orca-steps{padding-left:20px;line-height:1.55}.orca-steps li{margin-bottom:8px}
.orca-team{display:grid;gap:8px}.orca-member{border:1px solid var(--line);border-radius:10px;padding:9px 11px;background:#07101e}
.orca-member strong{display:block}.orca-member span{color:var(--muted);font-size:13px}
.orca-examples{display:grid;gap:8px}.orca-example{text-align:left;font-weight:600}
.orca-item{width:100%;text-align:left;border:1px solid var(--line);border-radius:12px;padding:12px;background:#07101e;color:var(--text)}
.orca-item.active{border-color:var(--blue)}
.orca-item small{color:var(--muted)}
.orca-check{display:flex;gap:8px;align-items:flex-start;margin-top:12px}
.orca-check input{width:auto;margin-top:3px}
.orca-tag{display:inline-flex;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:800;background:#12315e;color:#93c5fd}
.orca-tag.ok{background:#0f3b26;color:#86efac}.orca-tag.bad{background:#4c1414;color:#fca5a5}.orca-tag.wait{background:#463209;color:#fcd34d}
.orca-banner{border-radius:12px;padding:12px 14px;margin:12px 0;border:1px solid var(--line)}
.orca-banner.wait{border-color:#b45309;background:#2a1d06}.orca-banner.bad{border-color:#b91c1c;background:#2a0b0b}
.orca-task{border:1px solid var(--line);border-radius:12px;padding:12px;margin:10px 0;background:#07101e}
.orca-task h3{margin:0 0 6px;font-size:15px}
.orca-attempt{border-top:1px solid rgba(255,255,255,.07);padding-top:8px;margin-top:8px}
.orca-attempt pre{min-height:0;max-height:220px;overflow:auto;font-size:12px}
.orca-events{max-height:260px;overflow:auto;font-size:13px}
.orca-detail code{background:#050b15;border-radius:6px;padding:1px 5px}
</style>
"""

STATUS_LABELS = {
    "planning": ("Planning", ""), "awaiting_execution_approval": ("Needs your decision", "wait"),
    "building": ("Building", ""), "integration": ("Final checks", ""), "complete": ("Complete", "ok"),
    "complete_unverified": ("Complete (unverified)", "wait"), "escalated": ("Escalated", "bad"),
    "failed": ("Failed", "bad"), "paused": ("Paused", "wait"),
}


def render_orca_missions_script() -> str:
    labels = ",".join(f"'{key}':['{label}','{css}']" for key, (label, css) in STATUS_LABELS.items())
    return (r"""<script>
(function(){
  var LABELS={""" + labels + r"""};
  var section=null, openId=null, pollTimer=null, lastList='', lastDetail='', names={};
  function id(v){return document.getElementById(v)}
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function token(){return localStorage.getItem('mission_control_token')||''}
  async function post(path,body){
    var r=await fetch('/mission-control/orca/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({token:token()},body||{}))});
    var data=await r.json().catch(function(){return {status:'error',error:'Unreadable response from the server.'}});
    if(data.status==='unauthorized')throw new Error('Your Mission Control session has expired. Log in again.');
    if(!r.ok||data.status!=='ok')throw new Error(data.error||'Orca is unavailable.');
    return data;
  }
  function tag(status,running){var l=LABELS[status]||[status,''];return '<span class="orca-tag '+l[1]+'">'+esc(l[0])+(running?' &middot; working':'')+'</span>'}
  function install(){
    var main=document.querySelector('main');var nav=document.querySelector('.nav');
    if(!main||!nav||id('orca'))return false;
    section=document.createElement('section');section.id='orca';section.className='section';
    section.innerHTML=""" + json.dumps(ORCA_SECTION_HTML) + r""";main.appendChild(section);
    var btn=document.createElement('button');btn.dataset.section='orca';btn.textContent='🐋 Orca Missions';
    var after=nav.querySelector('button[data-section="execution"]');
    if(after&&after.nextSibling)nav.insertBefore(btn,after.nextSibling);else nav.appendChild(btn);
    btn.addEventListener('click',function(){if(window.showSection)window.showSection('orca');else{document.querySelectorAll('.section').forEach(function(s){s.classList.remove('active')});section.classList.add('active')}refreshAll()});
    id('orcaRefreshBtn').addEventListener('click',refreshAll);
    id('orcaStartBtn').addEventListener('click',startMission);
    section.querySelectorAll('.orca-example').forEach(function(b){b.addEventListener('click',function(){id('orcaGoal').value=this.textContent;id('orcaGoal').focus()})});
    if(window.location.hash==='#orca'){if(window.showSection)window.showSection('orca');refreshAll()}
    window.addEventListener('hashchange',function(){if(window.location.hash==='#orca')refreshAll()});
    pollTimer=setInterval(poll,5000);
    return true;
  }
  function visible(){return section&&section.classList.contains('active')}
  async function refreshAll(){loadWorkspaces();loadTeam();await refreshList();if(openId)openMission(openId)}
  async function loadTeam(){
    var box=id('orcaTeam');
    try{var data=await post('workforce');(data.team||[]).forEach(function(e){names[e.id]=e.name});
      box.innerHTML=(data.team||[]).map(function(e){return '<div class="orca-member"><strong>'+esc(e.name)+' <span class="orca-tag">'+esc(e.role)+'</span>'+'</strong><span>'+esc(e.summary)+'</span></div>'}).join('')||'<p class="muted">No employees found.</p>';}
    catch(err){box.innerHTML='<p class="warn">'+esc(err.message)+'</p>'}
  }
  function who(h,fallback){return esc(names[h.employee]||fallback)}
  async function loadWorkspaces(){
    var sel=id('orcaWorkspace');
    try{var data=await post('workspaces');var names=data.workspaces||[];
      sel.innerHTML=names.length?names.map(function(n){return '<option value="'+esc(n)+'">'+esc(n)+'</option>'}).join(''):'<option value="">No workspaces under '+esc(data.base)+'</option>';}
    catch(e){sel.innerHTML='<option value="">'+esc(e.message)+'</option>'}
  }
  async function refreshList(){
    var box=id('orcaMissionList');
    try{var data=await post('missions');var ms=data.missions||[];
      var key=JSON.stringify(ms)+'|'+openId;if(key===lastList&&box.childElementCount)return ms;lastList=key;
      if(!ms.length){box.innerHTML='<p class="muted">No missions yet. Start one on the right.</p>';return ms}
      box.innerHTML=ms.map(function(m){return '<button class="orca-item'+(m.mission_id===openId?' active':'')+'" data-id="'+esc(m.mission_id)+'"><strong>'+esc(m.goal.slice(0,110))+'</strong><br>'+tag(m.status,m.running)+' <small>'+esc(m.workspace)+' &middot; tasks '+m.tasks_passed+'/'+m.tasks_total+' &middot; '+esc(m.mission_id)+'</small></button>'}).join('');
      box.querySelectorAll('.orca-item').forEach(function(b){b.addEventListener('click',function(){openMission(this.dataset.id)})});
      return ms;}
    catch(e){box.innerHTML='<p class="warn">'+esc(e.message)+'</p>';return []}
  }
  async function startMission(){
    var msg=id('orcaStartMsg');msg.textContent='Starting...';
    try{var data=await post('start',{goal:id('orcaGoal').value,workspace:id('orcaWorkspace').value,execution_approved:id('orcaApproveExec').checked});
      msg.textContent='Mission '+data.mission.mission_id+' started. The architect is planning.';id('orcaGoal').value='';
      openId=data.mission.mission_id;await refreshList();openMission(openId);}
    catch(e){msg.textContent=e.message}
  }
  async function act(path,body,label){
    try{await post(path,Object.assign({mission_id:openId},body||{}));lastDetail='';await refreshList();openMission(openId)}
    catch(e){alert(label+' failed: '+e.message)}
  }
  async function openMission(mid){
    if(mid!==openId)lastDetail='';openId=mid;var box=id('orcaMissionDetail');
    document.querySelectorAll('.orca-item').forEach(function(b){b.classList.toggle('active',b.dataset.id===mid)});
    try{var data=await post('mission',{mission_id:mid});var key=JSON.stringify(data.mission);
      if(key===lastDetail)return;lastDetail=key;box.innerHTML=detailHtml(data.mission);bindActions(data.mission)}
    catch(e){box.innerHTML='<p class="warn">'+esc(e.message)+'</p>'}
  }
  function bindActions(m){
    var on=function(i,f){var el=id(i);if(el)el.addEventListener('click',f)};
    on('orcaApproveBtn',function(){act('decide-execution',{approved:true},'Approve')});
    on('orcaDeclineBtn',function(){act('decide-execution',{approved:false},'Decline')});
    on('orcaRunBtn',function(){act('run',{},'Run')});
    on('orcaRetryBtn',function(){act('retry',{},'Retry')});
  }
  function checksHtml(results){
    if(!results||!results.length)return '<p class="muted">Checks not run (execution not approved).</p>';
    return results.map(function(c){return '<div>'+(c.passed?'<span class="orca-tag ok">PASS</span>':'<span class="orca-tag bad">FAIL</span>')+' <code>'+esc(c.command)+'</code>'+(c.output?'<details><summary class="muted">output</summary><pre>'+esc(c.output)+'</pre></details>':'')+'</div>'}).join('');
  }
  function attemptsHtml(task){
    var prev=null;
    return (task.handoffs||[]).map(function(h){
      var divider='';if(h.kind==='build'){if(prev!==null&&h.attempt<=prev)divider='<div class="orca-banner wait">Founder retried this task: a fresh set of attempts starts here.</div>';prev=h.attempt}
      if(h.kind==='build')return divider+'<div class="orca-attempt"><strong>Attempt '+h.attempt+' &middot; '+who(h,'Builder')+'</strong><p>'+esc(h.summary)+'</p><p class="muted">Files: '+esc((h.files_changed||[]).join(', ')||'none listed')+'</p></div>';
      var issues=(h.issues||[]).map(function(i){return '<li><span class="orca-tag '+(i.severity==='blocker'?'bad':'')+'">'+esc(i.severity)+'</span> '+esc(i.detail)+'</li>'}).join('');
      return '<div class="orca-attempt"><strong>Attempt '+h.attempt+' &middot; '+who(h,h.kind==='ux_verdict'?'UX Designer':'QA Lead')+'</strong> '+(h.verdict==='PASS'?'<span class="orca-tag ok">PASS</span>':'<span class="orca-tag bad">FAIL</span>')+'<p>'+esc(h.evidence)+'</p>'+(issues?'<ul>'+issues+'</ul>':'')+checksHtml(h.check_results)+'</div>';
    }).join('')||'<p class="muted">Not started.</p>';
  }
  function detailHtml(m){
    var html='<div class="orca-detail"><h3>'+esc(m.goal)+'</h3><p>'+tag(m.status,m.running)+' <span class="muted">'+esc(m.mission_id)+' &middot; workspace '+esc(String(m.workspace_root).split('/').pop())+' &middot; execution '+esc(m.execution_approval)+'</span></p>';
    if(m.status==='awaiting_execution_approval')html+='<div class="orca-banner wait"><strong>Your decision:</strong> may Orca run this app\'s tests while building? Only test runners and read-only commands inside the workspace are allowed. If you decline, Orca still builds and reviews, but the result is unverified.<div class="actions"><button class="primary" id="orcaApproveBtn">Approve test runs</button><button class="secondary" id="orcaDeclineBtn">Decline</button></div></div>';
    if(m.status==='paused')html+='<div class="orca-banner wait"><strong>Paused:</strong> '+esc(m.paused_reason)+'<div class="actions"><button class="primary" id="orcaRunBtn">Resume</button></div></div>';
    if(m.status==='escalated')html+='<div class="orca-banner bad"><strong>Escalated:</strong> '+esc((m.escalation||{}).reason)+(m.tasks.some(function(t){return t.status==='escalated'})?'<div class="actions"><button class="primary" id="orcaRetryBtn">Give the task another 3 attempts</button></div>':'')+'</div>';
    if(!m.running&&['planning','building','integration'].indexOf(m.status)>=0)html+='<div class="orca-banner wait">Not currently running (for example after a server restart).<div class="actions"><button class="primary" id="orcaRunBtn">Run</button></div></div>';
    if(m.plan_summary)html+='<h3>Plan</h3><p>'+esc(m.plan_summary)+'</p>';
    html+=(m.tasks||[]).map(function(t){return '<div class="orca-task"><h3>'+esc(t.task_id)+' &middot; '+esc(t.title)+' <span class="orca-tag">'+esc(t.specialty||'general')+'</span> '+tag(t.status==='passed'?'complete':t.status==='escalated'?'escalated':'building')+' <small class="muted">attempts '+t.attempts+'/3</small></h3><p class="muted">'+esc(t.description)+'</p><p>Checks: '+(t.acceptance_checks||[]).map(function(c){return '<code>'+esc(c)+'</code>'}).join(' ')+'</p>'+attemptsHtml(t)+'</div>'}).join('');
    html+='<h3>Timeline</h3><ol class="orca-events">'+(m.events||[]).slice().reverse().slice(0,40).map(function(e){var extra=Object.keys(e).filter(function(k){return k!=='at'&&k!=='event'}).map(function(k){return k+'='+(typeof e[k]==='object'?JSON.stringify(e[k]):e[k])}).join(', ');return '<li><strong>'+esc(e.event)+'</strong> <span class="muted">'+esc(e.at)+'</span>'+(extra?'<br><small class="muted">'+esc(extra.slice(0,300))+'</small>':'')+'</li>'}).join('')+'</ol></div>';
    return html;
  }
  async function poll(){
    if(!visible())return;
    var ms=await refreshList();
    if(openId)openMission(openId);  // redraws only if the mission changed
  }
  if(!install()){document.addEventListener('DOMContentLoaded',install)}
})();
</script>""")
