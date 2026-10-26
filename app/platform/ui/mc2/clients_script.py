"""Mission Control Clients (step 3a): agency clients, their code, Health Checks and jobs.

Data: POST /mission-control/clients/* (founder-only, see app/platform/clients/service.py). Adding
code accepts an https Git URL or a folder on this Mac; fetching and Health Checks run in the
background and this screen polls while anything is running. Fix, feature, upgrade and care-plan
jobs can go to the AI team (step 4a): the founder confirms the client agreed to their code being
sent to the AI provider named in the dialog; the job then shows the mission's progress and its
changes. Finished work is delivered (step 4b) as a pull request on the client's GitHub repo (the
founder types the repository name to confirm) or as a patch download. Every server string goes
through esc(). A checked codebase can get the paid Audit (Code Auditor, same consent dialog as jobs):
its findings show here, each can become a job, and the PDF downloads.
"""
from __future__ import annotations

CLIENTS_SCRIPT = r"""
(function(){
  var MC=window.MC;var esc=MC.esc;var $=function(id){return document.getElementById(id)};
  var state={clients:[],selected:null,detail:null,timer:null,provider:'',changes:{},impact:{}};
  var LEVEL={contained:['Contained','done'],moderate:['Moderate','needs'],wide:['Wide','stuck']};
  var MISSION={planning:['Planning','run'],awaiting_execution_approval:['Needs your OK in Home','needs'],awaiting_decision:['Questions for you in Home','needs'],building:['Building','run'],
    integration:['Final checks','run'],paused:['Paused','needs'],complete:['Done and checked','done'],
    complete_unverified:['Done, not tested','needs'],escalated:['Stuck: needs you','stuck'],failed:['Failed','stuck']};
  var STATUS={lead:['Lead','plain'],active:['Active','run'],past:['Past','plain']};
  var JOB={lead:'Lead',quoted:'Quoted',in_progress:'In progress',delivered:'Delivered',paid:'Paid',closed:'Closed'};
  var KIND={health_check:'Health Check',audit:'Audit',fix:'Fix',feature:'Feature',upgrade:'Upgrade',care_plan:'Care plan'};
  var CB={added:'Waiting',fetching:'Fetching the code…',checking:'Running the Health Check…',ready:'Ready',failed:'Problem'};
  var TONE={A:'done',B:'done',C:'needs',D:'stuck',F:'stuck'};
  function tag(label,tone){return '<span class="mc-tag '+tone+'">'+esc(label)+'</span>'}
  function opts(map,current){return Object.keys(map).map(function(k){return '<option value="'+k+'"'+(k===current?' selected':'')+'>'+esc(map[k])+'</option>'}).join('')}
  function say(id,text,bad){var el=$(id);if(el){el.textContent=text||'';el.classList.toggle('bad',!!bad)}}
  function call(path,body){return MC.post('/mission-control/clients/'+path,body)}

  function bestGrade(c){var g=c.codebases.map(function(b){return b.last_check&&b.last_check.overall.grade}).filter(Boolean);return g.sort().pop()||null}
  function renderList(){
    var box=$('mcClientList');
    if(!state.clients.length){box.innerHTML='<li><p class="mc-empty">No clients yet. Add the first one above.</p></li>';return}
    box.innerHTML=state.clients.map(function(c){var open=c.jobs.filter(function(j){return ['delivered','paid','closed'].indexOf(j.status)<0}).length;
      var g=bestGrade(c),s=STATUS[c.status]||[c.status,'plain'];
      return '<li><button type="button" class="mc-row" data-client="'+esc(c.client_id)+'" aria-current="'+(c.client_id===state.selected)+'"><strong>'+esc(c.name)+'</strong>'+
        '<span class="mc-meta">'+tag(s[0],s[1])+(g?tag('Health '+g,TONE[g]||'plain'):'')+'<span>'+open+' open job'+(open===1?'':'s')+'</span></span></button></li>'}).join('');
  }
  function impactResultHtml(r){
    if(!r)return '';
    if(r.error)return '<p class="mc-status bad">'+esc(r.error)+'</p>';
    if(!r.found)return '<p class="mc-empty">'+esc(r.message)+(r.candidates&&r.candidates.length?' Did you mean: '+r.candidates.map(esc).join(', ')+'?':'')+'</p>';
    var lv=LEVEL[r.level]||[r.level,'plain'];
    function list(t,a){return a.length?'<p class="mc-empty">'+esc(t)+'</p><ul class="mc-changes">'+a.slice(0,12).map(function(x){return '<li><code>'+esc(x)+'</code></li>'}).join('')+(a.length>12?'<li class="mc-empty">and '+esc(a.length-12)+' more</li>':'')+'</ul>':''}
    return '<div class="mc-impact-result"><p>'+tag(lv[0]+' impact',lv[1])+' <strong>'+esc(r.name)+'</strong> <span class="mc-empty">('+esc(r.kind)+') · '+esc(r.affected_count)+' file'+(r.affected_count===1?'':'s')+' affected</span></p>'+
      '<p class="mc-empty">'+esc(r.advice)+'</p>'+list('Used directly by',r.used_directly_by.map(function(u){return u.path}))+list('Pages and entry points affected',r.entry_points)+
      list('Tests that cover it',r.tests)+'</div>';
  }
  function impactHtml(b){
    var im=b.last_check&&b.last_check.impact;if(!im||!im.files)return '';
    var top=(im.hotspots||[]).slice(0,3).map(function(h){return '<li><code>'+esc(h.path)+'</code> <span class="mc-empty">affects '+esc(h.affects)+' files</span></li>'}).join('');
    return '<details class="mc-impact"><summary>Impact map · '+esc(im.links)+' links between '+esc(im.linked_files)+' files</summary>'+
      (top?'<p class="mc-empty">Most connected (changes here ripple furthest):</p><ul class="mc-changes">'+top+'</ul>':'')+
      '<form class="mc-fields" data-impact="'+esc(b.codebase_id)+'"><label>What breaks if we change…?<input id="mcImpact-'+esc(b.codebase_id)+'" autocomplete="off" placeholder="a file, class, function, hook or package"></label>'+
      '<button type="submit" class="mc-btn secondary">Check impact</button></form>'+impactResultHtml(state.impact[b.codebase_id])+'</details>';
  }
  var SEV={critical:['Critical','stuck'],high:['High','stuck'],medium:['Medium','needs'],low:['Low','plain']};
  function auditHtml(b){
    var a=b.audit,html='<div class="mc-audit"><h4 class="mc-h4">Audit</h4>';
    if(a&&a.status==='running')return html+'<p>'+tag('Audit running…','run')+' <span class="mc-empty">The Code Auditor is reading the code. This takes a few minutes.</span></p></div>';
    if(a&&a.status==='failed')html+='<p class="mc-status bad">'+esc(a.error)+'</p>'+(MC.costText(a.cost)?'<p class="mc-empty">AI used before it stopped: '+esc(MC.costText(a.cost))+'</p>':'');
    if(a&&a.status==='ready'){
      html+='<p>'+Object.keys(a.counts).filter(function(k){return a.counts[k]}).map(function(k){return tag(a.counts[k]+' '+SEV[k][0].toLowerCase(),SEV[k][1])}).join(' ')+
        (a.unverified?' <span class="mc-empty">'+esc(a.unverified)+' not verified</span>':'')+
        (MC.costText(a.cost)?' <span class="mc-empty">· AI '+esc(MC.costText(a.cost))+'</span>':'')+'</p><p>'+esc(a.summary)+'</p>'+
        '<p class="mc-empty">Do these first:</p><ol class="mc-risks">'+a.first_steps.map(function(s){return '<li>'+esc(s)+'</li>'}).join('')+'</ol>'+
        '<details><summary>Fix plan ('+esc(a.findings.length)+')</summary><ol class="mc-findings">'+a.findings.map(function(f,i){var sv=SEV[f.severity]||[f.severity,'plain'];
          return '<li><strong>'+esc(f.title)+'</strong> '+tag(sv[0],sv[1])+(f.verified?'':' '+tag('Not verified','needs'))+
            '<br><span class="mc-empty">'+esc(f.size)+' · '+esc(f.hours)+' · '+esc(f.price)+(f.level?' · '+esc(f.level)+' impact, '+esc(f.affected)+' files':'')+'</span>'+
            '<br><button type="button" class="mc-btn secondary" data-finding="'+i+'" data-cb="'+esc(b.codebase_id)+'">Create a job from this</button></li>'}).join('')+'</ol></details>'+
        '<div class="mc-actions"><button type="button" class="mc-btn secondary" data-audit-pdf="'+esc(a.audit_id)+'" data-name="'+esc(b.label)+'">Download Audit PDF</button></div>'}
    if(b.last_check&&b.status==='ready'&&!b.running)html+='<div class="mc-actions"><button type="button" class="mc-btn" data-audit="'+esc(b.codebase_id)+'">'+(a?'Run the Audit again':'Run Audit')+'</button></div>';
    else if(!a)html+='<p class="mc-empty">Run the Health Check first; the Audit builds on it.</p>';
    return html+'</div>';
  }
  function codebaseHtml(b){
    var busy=b.running||b.status==='fetching'||b.status==='checking';
    var check=b.last_check?('<p>'+tag('Grade '+b.last_check.overall.grade,TONE[b.last_check.overall.grade]||'plain')+' '+esc(b.last_check.overall.score)+'/100 · checked '+esc(String(b.last_checked_at||'').slice(0,10))+'</p>'+
      (b.last_check.overall.grade_note?'<p class="mc-empty">'+esc(b.last_check.overall.grade_note)+'</p>':'')+
      '<ol class="mc-risks">'+b.last_check.top_risks.slice(0,3).map(function(r){return '<li><strong>'+esc(r.title)+'</strong> <span class="mc-empty">('+esc(r.severity)+')</span></li>'}).join('')+'</ol>'):'<p class="mc-empty">No Health Check yet.</p>';
    return '<li class="mc-card mc-codebase"><div class="mc-person-head"><h3>'+esc(b.label)+'</h3>'+tag(CB[b.status]||b.status,b.status==='failed'?'stuck':busy?'run':'plain')+'</div>'+
      '<p class="mc-empty">'+esc(b.source)+'</p>'+(b.error?'<p class="mc-status bad">'+esc(b.error)+'</p>':'')+check+
      impactHtml(b)+'<div class="mc-actions"><button type="button" class="mc-btn" data-check="'+esc(b.codebase_id)+'"'+(busy||b.status==='added'?' disabled':'')+'>'+(b.last_check?'Run again':'Run Health Check')+'</button>'+
      (b.has_report?'<button type="button" class="mc-btn secondary" data-pdf="'+esc(b.codebase_id)+'" data-name="'+esc(b.label)+'">Download PDF</button>':'')+'</div>'+auditHtml(b)+'</li>';
  }
  function changesHtml(w){
    var ch=state.changes[w.work_id];if(!ch)return '';
    if(ch.error)return '<p class="mc-status bad">'+esc(ch.error)+'</p>';
    if(!ch.files.length)return '<p class="mc-empty">No changes yet.</p>';
    return '<ul class="mc-changes">'+ch.files.map(function(f){return '<li><code>'+esc(f.path)+'</code> <span class="mc-empty">'+(f.added===null?'binary':'+'+esc(f.added)+' −'+esc(f.removed))+'</span></li>'}).join('')+'</ul>'+
      '<details><summary>Show the diff'+(ch.truncated?' (first part)':'')+'</summary><pre class="mc-diff">'+esc(ch.diff)+'</pre></details>';
  }
  function handoverHtml(m){
    var h=m.handover;if(!h)return '';
    if(h.error)return '<p class="mc-empty">'+esc(h.error)+'</p>';
    function list(t,a){return a&&a.length?'<p class="mc-empty">'+esc(t)+'</p><ul class="mc-changes">'+a.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul>':''}
    return '<details class="mc-handover"><summary>Handover note for the client</summary><p>'+esc(h.summary)+'</p>'+
      list('What changed',h.changes)+list('How to check it',h.how_to_test)+list('Good to know',h.watch_out)+'</details>';
  }
  function deliverHtml(w,m){
    if(!m.finished||['complete','complete_unverified'].indexOf(m.status)<0)return '';
    var pr=(w.deliveries||[]).filter(function(d){return d.kind==='pull_request'})[0];
    var html='<div class="mc-deliver"><h4 class="mc-h4">Deliver to the client</h4>'+
      (m.status==='complete_unverified'?'<p class="mc-empty">The project\'s tests were not run for this work; you\'ll be asked to confirm.</p>':'');
    if(pr)html+='<p>'+tag('Pull request sent','done')+' <a href="'+esc(pr.url)+'" target="_blank" rel="noopener noreferrer">Open on GitHub</a> <span class="mc-empty">'+esc(pr.target)+' · '+esc(pr.branch)+'</span></p>';
    html+='<div class="mc-actions">'+(!pr&&w.pr_target?'<button type="button" class="mc-btn" data-deliver="'+esc(w.work_id)+'" data-target="'+esc(w.pr_target)+'" data-unverified="'+(m.status==='complete_unverified')+'">Send pull request to '+esc(w.pr_target)+'</button>':'')+
      '<button type="button" class="mc-btn secondary" data-patch="'+esc(w.work_id)+'" data-unverified="'+(m.status==='complete_unverified')+'">Download patch</button></div>'+
      '<p class="mc-status" id="mcDeliver-'+esc(w.work_id)+'" aria-live="polite"></p></div>';
    return html;
  }
  function workHtml(j,c){
    if(!j.can_start_work)return '';
    var w=j.work,m=w&&w.mission,html='';
    if(m){var s=MISSION[m.status]||[m.status,'plain'];
      html+='<div class="mc-jobwork"><p>'+tag(s[0],s[1])+' <span class="mc-empty">AI team · tasks '+esc(m.tasks_passed)+'/'+esc(m.tasks_total)+(m.running?' · working…':'')+(MC.costText(m.cost)?' · AI '+esc(MC.costText(m.cost)):'')+'</span></p>'+
        (m.paused_reason?'<p class="mc-empty">'+esc(m.paused_reason)+'</p>':'')+(m.escalation?'<p class="mc-empty">'+esc(m.escalation)+'</p>':'')+
        '<div class="mc-actions"><a class="mc-btn secondary" href="#home">Open in Home</a><button type="button" class="mc-btn secondary" data-changes="'+esc(w.work_id)+'">See the changes</button></div>'+changesHtml(w)+handoverHtml(m)+deliverHtml(w,m)+'</div>'}
    if(m&&!m.finished)return html;
    var ready=c.codebases.filter(function(b){return b.status==='ready'&&!b.running});
    if(!ready.length)return html+'<p class="mc-empty">Add the client\'s code (and let it be checked) to hand this job to the AI team.</p>';
    var pick=ready.length>1?'<label class="mc-sr" for="mcWorkCb-'+esc(j.job_id)+'">Codebase for '+esc(j.title)+'</label><select class="mc-select" id="mcWorkCb-'+esc(j.job_id)+'">'+
      ready.map(function(b){return '<option value="'+esc(b.codebase_id)+'">'+esc(b.label)+'</option>'}).join('')+'</select>':'';
    return html+'<div class="mc-actions">'+pick+'<button type="button" class="mc-btn" data-start-work="'+esc(j.job_id)+'" data-codebase="'+esc(ready[0].codebase_id)+'">'+(m?'Start again with the AI team':'Start with the AI team')+'</button></div>';
  }
  function renderDetail(){
    var box=$('mcClientDetail'),c=state.detail;
    if(!c){box.innerHTML='<p class="mc-empty">Select a client to see their code, Health Checks and jobs.</p>';return}
    var jobs=c.jobs.length?'<ul class="mc-rows">'+c.jobs.map(function(j){return '<li class="mc-job"><div class="mc-job-head"><div><strong>'+esc(j.title)+'</strong><small>'+esc(KIND[j.kind]||j.kind)+(j.price?' · '+esc(j.price):'')+'</small></div>'+
      '<label class="mc-sr" for="mcJob-'+esc(j.job_id)+'">Status of '+esc(j.title)+'</label><select class="mc-select" id="mcJob-'+esc(j.job_id)+'" data-job="'+esc(j.job_id)+'">'+opts(JOB,j.status)+'</select></div>'+workHtml(j,c)+'</li>'}).join('')+'</ul>':'<p class="mc-empty">No jobs yet.</p>';
    box.innerHTML='<div class="mc-person-head"><h3>'+esc(c.name)+'</h3><label class="mc-sr" for="mcClientStatus">Client status</label><select class="mc-select" id="mcClientStatus">'+opts({lead:'Lead',active:'Active',past:'Past'},c.status)+'</select></div>'+
      (c.contact?'<p class="mc-empty">'+esc(c.contact)+'</p>':'')+
      '<h3 class="mc-h3">Code</h3><ul class="mc-team">'+(c.codebases.map(codebaseHtml).join('')||'<li class="mc-empty">No code connected yet.</li>')+'</ul>'+
      '<form class="mc-fields" id="mcAddCode"><label>Git URL (https) or folder on this Mac<input id="mcCodeSource" autocomplete="off" placeholder="https://github.com/client/app or /Users/you/client-app" required></label>'+
      '<label>Name (optional)<input id="mcCodeLabel" autocomplete="off"></label><button type="submit" class="mc-btn secondary">Add code</button></form><p class="mc-status" id="mcCodeStatus" aria-live="polite"></p>'+
      '<h3 class="mc-h3">Jobs</h3>'+jobs+
      '<form class="mc-fields" id="mcAddJob"><label>New job<input id="mcJobTitle" autocomplete="off" placeholder="e.g. Upgrade PHP 7.4 to 8.3" required></label>'+
      '<label>Kind<select id="mcJobKind">'+opts(KIND,'fix')+'</select></label><label>Price<input id="mcJobPrice" autocomplete="off" placeholder="$99 fixed"></label>'+
      '<button type="submit" class="mc-btn secondary">Add job</button></form><p class="mc-status" id="mcJobStatus" aria-live="polite"></p>';
  }

  async function loadList(){try{var d=await call('list');state.clients=d.clients||[];renderList()}catch(e){$('mcClientList').innerHTML='<li><p class="mc-empty">'+esc(e.message)+'</p></li>'}}
  async function loadDetail(){
    var key=state.selected;
    if(!key){state.detail=null;renderDetail();return}
    var d=null;try{d=await call('detail',{client_id:key})}catch(e){d=null}
    if(state.selected!==key)return;  // the founder picked another client meanwhile: drop this reply
    state.detail=d&&d.client||null;state.provider=d&&d.ai_provider||'';
    var active=document.activeElement&&document.activeElement.closest&&document.activeElement.closest('#mcClientDetail form');
    if(!active)renderDetail();
    var busy=state.detail&&(state.detail.codebases.some(function(b){return b.running||b.status==='fetching'||b.status==='checking'||(b.audit&&b.audit.status==='running')})||
      state.detail.jobs.some(function(j){return j.work&&j.work.mission&&j.work.mission.running}));
    clearTimeout(state.timer);if(busy)state.timer=setTimeout(function(){loadDetail();loadList()},3000);
  }
  // ---- Security alerts (company/security-alerts.yaml): check every client's code, offline ----
  var ALERT={affected:['Affected','stuck'],check_server:['Check the server','needs'],patched:['Patched','done'],not_applicable:['Not used','plain'],missing:['Code missing','plain']};
  state.alerts=[];state.sweeps={};
  function safeUrl(u){return /^https:\/\//.test(String(u||''))?u:''}
  function alertHtml(a){
    var sw=state.sweeps[a.id],rows='';
    if(sw&&sw.error)rows='<p class="mc-status bad">'+esc(sw.error)+'</p>';
    else if(sw){var hit=sw.results.filter(function(r){return r.status!=='not_applicable'});
      rows=hit.length?'<ul class="mc-rows">'+hit.map(function(r,i){var s=ALERT[r.status]||[r.status,'plain'];
        return '<li><div><strong>'+esc(r.client_name||'Client')+'</strong> · '+esc(r.label)+'<small>'+esc(r.reason)+'</small></div>'+tag(s[0],s[1])+
          (r.status==='affected'||r.status==='check_server'?'<button type="button" class="mc-btn secondary" data-alert-job="'+esc(a.id)+'" data-row="'+i+'">Create upgrade job</button>':'')+'</li>'}).join('')+'</ul>'
        :'<p class="mc-empty">No client codebase uses this.</p>'}
    var link=safeUrl(a.source);
    return '<article class="mc-alert"><div class="mc-person-head"><h3>'+esc(a.title)+'</h3>'+tag(String(a.severity||'').replace(/^./,function(c){return c.toUpperCase()}),a.severity==='critical'||a.severity==='high'?'stuck':'needs')+'</div>'+
      '<p class="mc-empty">'+esc(a.id)+' · '+esc(a.published)+(a.cves&&a.cves.length?' · '+esc(a.cves.join(', ')):'')+(link?' · <a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">Source</a>':'')+'</p>'+
      '<p>'+esc(a.summary)+'</p>'+(a.mitigation&&a.mitigation.length?'<details><summary>What to do</summary><ul class="mc-changes">'+a.mitigation.map(function(m){return '<li>'+esc(m)+'</li>'}).join('')+'</ul></details>':'')+
      '<div class="mc-actions"><button type="button" class="mc-btn" data-sweep="'+esc(a.id)+'">'+(sw?'Check again':'Check all clients')+'</button></div>'+rows+'</article>';
  }
  function renderAlerts(){var box=$('mcAlertList');if(!box)return;
    box.innerHTML=state.alerts.length?state.alerts.map(alertHtml).join(''):'<p class="mc-empty">No alerts tracked. Add them in company/security-alerts.yaml.</p>'}
  async function loadAlerts(){try{var d=await call('security-alerts');state.alerts=d.alerts||[]}catch(e){state.alerts=[]}renderAlerts()}
  $('mcAlertList')&&$('mcAlertList').addEventListener('click',async function(e){
    var go=e.target.closest('[data-sweep]'),mk=e.target.closest('[data-alert-job]');
    if(go){go.disabled=true;go.textContent='Checking…';var d=await call('alert-sweep',{alert_id:go.dataset.sweep});
      state.sweeps[go.dataset.sweep]=d.error?{error:d.error}:{results:(d.results||[]).filter(function(r){return r.status!=='not_applicable'})};renderAlerts();return}
    if(mk){var a=state.alerts.filter(function(x){return x.id===mk.dataset.alertJob})[0],r=state.sweeps[a.id].results[+mk.dataset.row],job=a.job||{};
      mk.disabled=true;var res=await call('add-job',{client_id:r.client_id,title:(job.title||('Fix '+a.id)).slice(0,200),kind:job.kind||'upgrade',
        notes:(r.label+': '+r.reason+'\n\nWhat to do:\n- '+(a.mitigation||[]).join('\n- ')+'\n\nSource: '+(a.source||'')+' ('+a.id+')').slice(0,4000)});
      if(res.error){window.alert(res.error);mk.disabled=false;return}mk.textContent='Job created';loadList();if(state.selected===r.client_id)loadDetail()}
  });
  MC.onShow=MC.onShow||{};MC.onShow.clients=function(){loadList();loadDetail();loadAlerts()};

  $('mcAddClient').addEventListener('submit',async function(e){
    e.preventDefault();say('mcAddClientStatus','Adding…');
    try{var d=await call('create',{name:$('mcClientName').value,contact:$('mcClientContact').value});if(d.error)throw new Error(d.error);
      $('mcClientName').value='';$('mcClientContact').value='';say('mcAddClientStatus','');state.selected=d.client.client_id;await loadList();loadDetail()}
    catch(err){say('mcAddClientStatus',err.message,true)}
  });
  $('mcClientList').addEventListener('click',function(e){var b=e.target.closest('[data-client]');if(!b)return;state.selected=b.dataset.client;renderList();loadDetail()});
  $('mcClientDetail').addEventListener('change',async function(e){
    var t=e.target;
    if(t.id==='mcClientStatus'){await call('update',{client_id:state.selected,status:t.value});loadList()}
    else if(t.dataset.job){await call('update-job',{job_id:t.dataset.job,status:t.value});loadList()}
  });
  $('mcClientDetail').addEventListener('submit',async function(e){
    e.preventDefault();var f=e.target;
    if(f.dataset.impact){var cb=f.dataset.impact,q=$('mcImpact-'+cb).value.trim();if(!q)return;
      var r=await call('impact',{codebase_id:cb,target:q});state.impact[cb]=r.error?{error:r.error}:r.impact;
      document.activeElement&&document.activeElement.blur&&document.activeElement.blur();renderDetail();
      var box=document.querySelector('[data-impact="'+cb+'"]');if(box){box.closest('details').open=true;$('mcImpact-'+cb).value=q}return}
    if(f.id==='mcAddCode'){say('mcCodeStatus','Adding…');
      var d=await call('add-codebase',{client_id:state.selected,source:$('mcCodeSource').value,label:$('mcCodeLabel').value});
      if(d.error){say('mcCodeStatus',d.error,true);return}f.reset();say('mcCodeStatus','')}
    else if(f.id==='mcAddJob'){say('mcJobStatus','Adding…');
      var j=await call('add-job',{client_id:state.selected,title:$('mcJobTitle').value,kind:$('mcJobKind').value,price:$('mcJobPrice').value});
      if(j.error){say('mcJobStatus',j.error,true);return}f.reset();say('mcJobStatus','')}
    document.activeElement&&document.activeElement.blur&&document.activeElement.blur();loadDetail();loadList();
  });
  $('mcClientDetail').addEventListener('click',async function(e){
    var run=e.target.closest('[data-check]'),pdf=e.target.closest('[data-pdf]'),go=e.target.closest('[data-start-work]'),diff=e.target.closest('[data-changes]'),
      send=e.target.closest('[data-deliver]'),patch=e.target.closest('[data-patch]'),
      aud=e.target.closest('[data-audit]'),apdf=e.target.closest('[data-audit-pdf]'),fnd=e.target.closest('[data-finding]');
    if(aud){var cd=state.detail,cbx=cd.codebases.filter(function(b){return b.codebase_id===aud.dataset.audit})[0];
      if(!window.confirm('The Code Auditor will read "'+cbx.label+'" for '+cd.name+' and write the Audit (a few minutes). Nothing is changed or run outside the sandbox.\n\n'+
        'To do this, the code is sent to '+state.provider+'. Only continue if '+cd.name+' agreed to that.'))return;
      aud.disabled=true;var ra=await call('run-audit',{codebase_id:aud.dataset.audit,client_consent:true,ai_provider:state.provider});
      if(ra.error)window.alert(ra.error);loadDetail();return}
    if(apdf){var ar=await fetch('/mission-control/clients/audit-report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:MC.token(),audit_id:apdf.dataset.auditPdf})});
      if(!ar.ok){window.alert('The Audit report could not be downloaded.');return}
      var aurl=URL.createObjectURL(await ar.blob()),aa=document.createElement('a');aa.href=aurl;aa.download=(apdf.dataset.name||'client')+'-audit.pdf';
      document.body.appendChild(aa);aa.click();aa.remove();setTimeout(function(){URL.revokeObjectURL(aurl)},1000);return}
    if(fnd){var cbf=state.detail.codebases.filter(function(b){return b.codebase_id===fnd.dataset.cb})[0],f=cbf.audit.findings[+fnd.dataset.finding];
      fnd.disabled=true;var rj=await call('add-job',{client_id:state.selected,title:f.title.slice(0,200),kind:'fix',price:f.price,
        notes:(f.fix+(f.evidence.length?'\n\nEvidence: '+f.evidence.join(', '):'')+'\n\nFrom the Audit.').slice(0,4000)});
      if(rj.error){window.alert(rj.error);fnd.disabled=false;return}fnd.textContent='Job created';loadDetail();loadList();return}
    if(send){var target=send.dataset.target,unv=send.dataset.unverified==='true';
      var typed=window.prompt('This pushes one new branch to '+target+' and opens a pull request for the client to review. Nothing is merged.\n\nType '+target+' to confirm.');
      if(typed===null)return;
      if(typed.trim()!==target){window.alert('That doesn\'t match '+target+'; nothing was sent.');return}
      if(unv&&!window.confirm('The project\'s tests were not run for this work. Send it anyway?'))return;
      send.disabled=true;say('mcDeliver-'+send.dataset.deliver,'Sending the pull request…');
      var r=await call('deliver',{work_id:send.dataset.deliver,confirm_repository:typed.trim(),accept_unverified:unv});
      if(r.error){say('mcDeliver-'+send.dataset.deliver,r.error,true);send.disabled=false;return}
      loadDetail();return}
    if(patch){var unvp=patch.dataset.unverified==='true';
      if(unvp&&!window.confirm('The project\'s tests were not run for this work. Download the patch anyway?'))return;
      var pr=await fetch('/mission-control/clients/patch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:MC.token(),work_id:patch.dataset.patch,accept_unverified:unvp})});
      if(!pr.ok){window.alert('There is no finished patch to download.');return}
      var name=((pr.headers.get('Content-Disposition')||'').match(/filename="([^"]+)"/)||[])[1]||'changes.patch';
      var purl=URL.createObjectURL(await pr.blob()),pa=document.createElement('a');pa.href=purl;pa.download=name;
      document.body.appendChild(pa);pa.click();pa.remove();setTimeout(function(){URL.revokeObjectURL(purl)},1000);loadDetail();return}
    if(go){var c=state.detail,job=go.dataset.startWork,sel=$('mcWorkCb-'+job),cb=sel?sel.value:go.dataset.codebase;
      var label=(c.codebases.filter(function(b){return b.codebase_id===cb})[0]||{}).label||'the code';
      if(!window.confirm('The AI team will work on a copy of "'+label+'" for '+c.name+'. Commands run in the sandbox, and the client\'s original code is never changed.\n\n'+
        'To do this, the code is sent to '+state.provider+'. Only continue if '+c.name+' agreed to that.'))return;
      go.disabled=true;var r=await call('start-work',{job_id:job,codebase_id:cb,client_consent:true,ai_provider:state.provider});
      if(r.error)window.alert(r.error);loadDetail();loadList();return}
    if(diff){var wid=diff.dataset.changes;diff.disabled=true;var ch=await call('work-changes',{work_id:wid});
      state.changes[wid]=ch.error?{error:ch.error}:ch;renderDetail();return}
    if(run){run.disabled=true;var d=await call('run-check',{codebase_id:run.dataset.check});if(d.error)window.alert(d.error);loadDetail()}
    if(pdf){var r=await fetch('/mission-control/clients/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:MC.token(),codebase_id:pdf.dataset.pdf})});
      if(!r.ok){window.alert('The report could not be downloaded.');return}
      var url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download=(pdf.dataset.name||'client')+'-health-check.pdf';
      document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(url)},1000)}
  });
})();
"""
