"""Mission Control v2 core + Home: session, navigation, "Needs you" and "All work".

Data comes from existing founder-only APIs: Orca missions (/mission-control/orca/*), the active
platform mission (GET /mission-control/execution) and publish requests
(/mission-control/publish-requests/list). Every server or AI-written string goes through esc()
before it touches innerHTML. The page polls every 5s while Home is visible and only redraws
when the data changed.
"""
from __future__ import annotations

HOME_SCRIPT = r"""
(function(){
  var TOKEN_KEY='mission_control_token';
  var MC=window.MC={};
  MC.token=function(){try{return localStorage.getItem(TOKEN_KEY)||''}catch(e){return ''}};
  MC.esc=function(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})};
  MC.post=async function(url,body){
    var r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({token:MC.token()},body||{}))});
    var data=await r.json().catch(function(){return {status:'error',error:'Unreadable response from the server.'}});
    if(data&&(data.status==='unauthorized'||data.authenticated===false)){MC.toLogin();throw new Error('Your session has expired.')}
    if(!r.ok)throw new Error((data&&data.error)||('Request failed ('+r.status+')'));
    return data;
  };
  MC.toLogin=function(){window.location.href='/mission-control/ui'};
  var $=function(id){return document.getElementById(id)};
  var esc=MC.esc;

  // ---- navigation -----------------------------------------------------------------------
  MC.showPage=function(name){
    var pages=document.querySelectorAll('[data-mc-page]');var found=false;
    pages.forEach(function(p){var on=p.dataset.mcPage===name;p.hidden=!on;if(on)found=true});
    if(!found){name='home';$('mc-home').hidden=false}
    document.querySelectorAll('[data-mc-nav]').forEach(function(a){if(a.dataset.mcNav===name)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
    if(name==='home')refresh();
  };
  window.addEventListener('hashchange',function(){MC.showPage((location.hash||'#home').slice(1))});

  // ---- data -----------------------------------------------------------------------------
  var state={orca:[],platform:null,publish:[],filter:'all',selected:null,lastKey:'',lastDetail:''};
  var LABEL={planning:['Planning','run'],awaiting_execution_approval:['Needs your decision','needs'],building:['Building','run'],
    integration:['Final checks','run'],paused:['Paused','needs'],escalated:['Stuck — needs you','stuck'],failed:['Failed','stuck'],
    complete:['Done · checks passed','done'],complete_unverified:['Done · not verified','done']};
  var WORKING={planning:1,building:1,integration:1};
  function stopped(m){return WORKING[m.status]&&!m.running}
  function group(status,m){if(m&&stopped(m))return 'needs';if(status==='awaiting_execution_approval'||status==='paused'||status==='escalated')return 'needs';
    if(status==='complete'||status==='complete_unverified'||status==='failed')return 'done';return 'run'}
  function tag(label,tone){return '<span class="mc-tag '+tone+'">'+esc(label)+'</span>'}
  function when(iso){var d=new Date(iso);return isNaN(d)?'':d.toLocaleDateString(undefined,{day:'numeric',month:'short'})+' '+d.toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'})}
  var names={};
  function who(id){return names[id]||String(id||'the team').replace(/_/g,' ')}
  MC.post('/mission-control/orca/workforce').then(function(r){(r.team||[]).forEach(function(e){names[e.id]=e.name})}).catch(function(){});

  async function load(){
    var results=await Promise.allSettled([MC.post('/mission-control/orca/missions'),
      fetch('/mission-control/execution').then(function(r){return r.json()}),MC.post('/mission-control/publish-requests/list')]);
    state.orca=results[0].status==='fulfilled'?(results[0].value.missions||[]):[];
    var exec=results[1].status==='fulfilled'?results[1].value:null;
    state.platform=exec&&exec.active_mission?exec.active_mission:null;
    state.publish=results[2].status==='fulfilled'?(results[2].value.requests||[]).filter(function(r){return r.build_completed}):[];
    state.errors=results.filter(function(r){return r.status==='rejected'}).map(function(r){return r.reason&&r.reason.message});
  }
  function items(){
    var list=state.orca.map(function(m){var l=LABEL[m.status]||[m.status,'run'];
      if(stopped(m))l=['Stopped — not running','needs'];
      return {id:'orca:'+m.mission_id,kind:'orca',mission:m,title:m.goal,app:m.workspace,group:group(m.status,m),label:m.running&&group(m.status,m)!=='done'?'Working · '+l[0]:l[0],tone:l[1],
        sub:m.workspace+(m.origin==='board_room'?' · from Jarvis':'')+' · tasks '+m.tasks_passed+'/'+m.tasks_total+' · '+when(m.created_at)+' · '+String(m.mission_id).slice(-6)}});
    if(state.platform){var p=state.platform;list.unshift({id:'platform',kind:'platform',mission:p,title:p.title||p.founder_request||'Platform mission',app:'Platform',
      group:p.blocker?'needs':(String(p.status).indexOf('complete')>=0?'done':'run'),label:'Platform change · '+(p.current_stage||p.status||'in progress'),tone:p.blocker?'stuck':'plain',sub:'Platform change'})}
    return list;
  }

  // ---- Needs you ------------------------------------------------------------------------
  function decisionCard(kind,tone,title,text,buttons){
    return '<article class="mc-card mc-decision"><div class="mc-text">'+tag(kind,tone)+'<h3>'+esc(title)+'</h3><p>'+esc(text)+'</p></div><div class="mc-actions">'+buttons+'</div></article>'}
  function btn(label,attrs,cls){return '<button type="button" class="mc-btn '+(cls||'')+'" '+attrs+'>'+esc(label)+'</button>'}
  function renderNeeds(){
    var cards=[];
    state.orca.forEach(function(m){var id=esc(m.mission_id);
      if(m.status==='awaiting_execution_approval')cards.push(decisionCard('Your decision','needs','May the team run the tests for “'+m.goal+'”?',
        'The plan is ready in '+m.workspace+'. Only test runners and read-only commands, inside that app.',
        btn('Approve test runs','data-act="approve" data-id="'+id+'"')+btn('Decline','data-act="decline" data-id="'+id+'"','secondary')+btn('See the plan','data-act="open" data-id="'+id+'"','quiet')));
      else if(m.status==='escalated')cards.push(decisionCard('Stuck after 3 tries','stuck',m.goal,m.escalation||'A task kept failing review.',
        btn('Give it another round','data-act="retry" data-id="'+id+'"')+btn('Read what happened','data-act="open" data-id="'+id+'"','quiet')));
      else if(stopped(m))cards.push(decisionCard('Stopped','needs',m.goal,'This mission stopped (for example after a server restart) while it was '+(LABEL[m.status]||[m.status])[0].toLowerCase()+'.',
        btn('Resume','data-act="run" data-id="'+id+'"')+btn('Details','data-act="open" data-id="'+id+'"','quiet')));
      else if(m.status==='paused'&&!m.running)cards.push(decisionCard('Paused','needs',m.goal,m.paused_reason||'The AI provider was unavailable.',
        btn('Resume','data-act="run" data-id="'+id+'"')+btn('Details','data-act="open" data-id="'+id+'"','quiet')));});
    state.publish.forEach(function(r){cards.push(decisionCard('Ready to publish','run',r.project_name||'Customer build',
      'Requested by '+(r.owner||'a customer')+'. Nothing goes live until you approve it.','<a class="mc-btn" href="/mission-control/ui#deployments">Review</a>'))});
    if(state.platform&&state.platform.blocker)cards.push(decisionCard('Platform change blocked','stuck',state.platform.title||'Platform mission',
      state.platform.blocker,'<a class="mc-btn" href="/mission-control/ui#execution">Review in classic</a>'));
    $('mcNeedsYou').innerHTML=cards.join('')||'<p class="mc-empty">Nothing needs you right now.</p>';
    var running=items().filter(function(i){return i.group==='run'}).length;
    $('mcSummary').textContent=(cards.length?cards.length+' thing'+(cards.length===1?' needs':'s need')+' you':'Nothing needs you')+' · '+running+' running'+
      (state.errors&&state.errors.length?' · some data could not load':'');
  }

  // ---- All work -------------------------------------------------------------------------
  function renderWork(){
    var all=items();
    var tabs=[['all','All'],['needs','Needs you'],['run','Running'],['done','Done']];
    $('mcTabs').innerHTML=tabs.map(function(t){var n=all.filter(function(i){return t[0]==='all'||i.group===t[0]}).length;
      return '<button type="button" role="tab" aria-selected="'+(state.filter===t[0])+'" data-filter="'+t[0]+'">'+t[1]+' ('+n+')</button>'}).join('');
    var shown=all.filter(function(i){return state.filter==='all'||i.group===state.filter});
    if(!shown.some(function(i){return i.id===state.selected}))state.selected=shown.length?shown[0].id:null;
    $('mcWorkList').innerHTML=shown.map(function(i){return '<li><button type="button" class="mc-row" data-select="'+esc(i.id)+'" aria-current="'+(i.id===state.selected)+'"><strong>'+esc(i.title)+'</strong><span class="mc-meta">'+tag(i.label,i.tone)+'<span>'+esc(i.sub)+'</span></span></button></li>'}).join('')||
      '<li><p class="mc-empty">No work here yet. Ask Jarvis to start something.</p></li>';
    renderDetail();
  }
  async function renderDetail(){
    var key=state.selected;var item=items().find(function(i){return i.id===key});var box=$('mcDetail');
    if(!item){state.lastDetail=null;box.innerHTML='<p class="mc-empty">Select a job to see its plan and progress.</p>';return}
    var html;
    if(item.kind==='platform'){var p=item.mission;
      html=tag(item.label,item.tone)+'<h3>'+esc(item.title)+'</h3><div class="mc-next"><span>Next</span><p>'+esc(p.blocker||p.next_recommended_action||'In progress.')+'</p></div>'+
        '<ol class="mc-tasks">'+(p.stages||[]).map(function(s){return '<li class="mc-task"><div class="mc-task-head"><span>'+esc(s.label)+'</span>'+tag(s.completed?'Done':(s.status||'waiting'),s.completed?'done':'plain')+'</div></li>'}).join('')+'</ol>'+
        '<a class="mc-btn secondary" href="/mission-control/ui#execution">Open in classic Mission Control</a>';
    }else{
      // A newer click or refresh may have changed the selection while this was loading: drop stale replies.
      var data;try{data=(await MC.post('/mission-control/orca/mission',{mission_id:item.mission.mission_id})).mission}
      catch(e){if(state.selected!==key)return;state.lastDetail=null;box.innerHTML='<p class="mc-empty">'+esc(e.message)+'</p>';return}
      if(state.selected!==key)return;
      html=orcaDetail(item,data);
    }
    if(html===state.lastDetail)return;state.lastDetail=html;box.innerHTML=html;
  }
  function orcaDetail(item,m){
    var next={awaiting_execution_approval:'The plan is ready. Decide in “Needs you” whether the team may run this app’s tests.',paused:m.paused_reason,
      escalated:(m.escalation||{}).reason,planning:'The Software Architect is planning.',building:'The team is building. Nothing needed from you.',
      integration:'All tasks passed; running the final checks together.',complete:'Finished and verified. Nothing goes live until you publish.',
      complete_unverified:'Finished, but not verified: test runs were declined.',failed:'Planning failed. Ask Jarvis to try again with a clearer goal.'}[m.status]||m.status;
    var tasks=(m.tasks||[]).map(function(t){var last={};(t.handoffs||[]).forEach(function(h){last[h.kind]=h});
      var trail=[last.build?'Built by the '+who(last.build.employee):'Not started',last.qa_verdict?'QA '+last.qa_verdict.verdict:'',last.ux_verdict?'UX '+last.ux_verdict.verdict:''].filter(Boolean).join(' · ');
      var tone=t.status==='passed'?'done':t.status==='escalated'?'stuck':'plain';
      var hist=(t.handoffs||[]).map(function(h){var head='Attempt '+h.attempt+' · '+(h.kind==='build'?'build':h.kind==='ux_verdict'?'UX review':'QA review')+(h.verdict?' · '+h.verdict:'');
        var issues=(h.issues||[]).map(function(i){return '['+i.severity+'] '+i.detail}).join('\n');
        var checks=(h.check_results||[]).map(function(c){return (c.passed?'PASS ':'FAIL ')+c.command+(c.output?'\n'+c.output:'')}).join('\n');
        return head+'\n'+(h.summary||h.evidence||'')+(issues?'\n'+issues:'')+(checks?'\n'+checks:'')}).join('\n\n');
      return '<li class="mc-task"><div class="mc-task-head"><span>'+esc(t.task_id+' · '+t.title)+'</span>'+tag(t.status==='passed'?'Passed':t.status==='escalated'?'Stuck':'Attempt '+t.attempts+' of 3',tone)+'</div><small>'+esc((t.specialty||'general')+' · '+trail)+'</small>'+
        (hist?'<details><summary>Full history and check output</summary><pre>'+esc(hist)+'</pre></details>':'')+'</li>'}).join('');
    return tag(item.label,item.tone)+'<h3>'+esc(m.goal)+'</h3><p class="mc-empty">'+esc(item.sub)+'</p><div class="mc-next"><span>Next</span><p>'+esc(next||'')+'</p></div>'+
      (m.plan_summary?'<p>'+esc(m.plan_summary)+'</p>':'')+'<ol class="mc-tasks">'+(tasks||'<li class="mc-empty">No tasks yet.</li>')+'</ol>';
  }

  // ---- actions --------------------------------------------------------------------------
  async function act(kind,id,el){
    var calls={approve:['decide-execution',{approved:true}],decline:['decide-execution',{approved:false}],run:['run',{}],retry:['retry',{}]};
    if(kind==='open'){state.selected='orca:'+id;state.filter='all';state.lastDetail='';renderWork();$('mcDetail').scrollIntoView({behavior:'smooth',block:'start'});return}
    var c=calls[kind];if(!c)return;el.disabled=true;
    try{var r=await MC.post('/mission-control/orca/'+c[0],Object.assign({mission_id:id},c[1]));if(r.status!=='ok')throw new Error(r.error||'Orca refused the action.');
      state.selected='orca:'+id;await refresh(true)}catch(e){alert(e.message)}finally{el.disabled=false}
  }
  document.addEventListener('click',function(ev){
    var t=ev.target.closest('[data-act],[data-filter],[data-select]');if(!t)return;
    if(t.dataset.act)act(t.dataset.act,t.dataset.id,t);
    else if(t.dataset.filter){state.filter=t.dataset.filter;renderWork()}
    else if(t.dataset.select){state.selected=t.dataset.select;state.lastDetail='';renderWork()}
  });

  async function refresh(force){
    await load();var key=JSON.stringify([state.orca,state.platform,state.publish]);
    if(!force&&key===state.lastKey){renderDetail();return}state.lastKey=key;renderNeeds();renderWork();
  }
  MC.refreshHome=function(){return refresh(true)};
  setInterval(function(){var home=$('mc-home');if(home&&!home.hidden&&!document.hidden)refresh(false)},5000);

  // ---- start ----------------------------------------------------------------------------
  (async function(){
    if(!MC.token()){MC.toLogin();return}
    try{var s=await fetch('/mission-control/auth/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:MC.token()})}).then(function(r){return r.json()});
      if(!s.authenticated){MC.toLogin();return}}catch(e){}
    MC.showPage((location.hash||'#home').slice(1));
  })();
})();
"""
