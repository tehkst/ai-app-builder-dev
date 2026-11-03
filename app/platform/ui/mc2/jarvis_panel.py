"""Mission Control v2: the Jarvis panel, the one place to type, available on every screen.

Talks to the existing Board Room chat (POST /mission-control/operating-console/chat) with the same
payload the classic page sends ({token, message, conversation_id, conversation_history}) and runs
the same action buttons Jarvis returns (post / post_secondary / function / show_section / copy /
note). Replies are shown as plain text (escaped, line breaks kept). The conversation id and
the last messages are kept in localStorage for this viewer only.
"""
from __future__ import annotations

JARVIS_PANEL_HTML = """
<aside class="mc-jarvis" id="mcJarvis" aria-label="Jarvis" hidden>
  <div class="mc-jarvis-head">
    <div><h2>Jarvis</h2><span class="mc-empty" style="font-size:13px">Available on every screen</span></div>
    <button type="button" class="mc-btn secondary" id="mcJarvisClose" aria-label="Close Jarvis">Close</button>
  </div>
  <ol class="mc-convo" id="mcConvo" aria-live="polite" aria-label="Conversation"></ol>
  <form class="mc-composer" id="mcComposer">
    <label for="mcJarvisInput">Message Jarvis</label>
    <textarea id="mcJarvisInput" rows="3" placeholder="Ask anything, or describe a change. Name the app if it’s for a customer app."></textarea>
    <button type="submit" class="mc-btn" id="mcJarvisSend">Send</button>
  </form>
</aside>
"""

JARVIS_SCRIPT = r"""
(function(){
  var MC=window.MC;var $=function(id){return document.getElementById(id)};var esc=MC.esc;
  var KEY='mc2_jarvis_conversation',OPEN='mc2_jarvis_open',MAX=40;
  function store(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch(e){return null}}
  function save(c){try{localStorage.setItem(KEY,JSON.stringify(c))}catch(e){}}
  var convo=store()||{id:'MC2-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,8),messages:[]};
  var busy=false;

  function setOpen(open){$('mcJarvis').hidden=!open;document.querySelectorAll('.mc-open-jarvis').forEach(function(b){b.hidden=open});
    try{localStorage.setItem(OPEN,open?'1':'0')}catch(e){}if(open){render();$('mcJarvisInput').focus()}}
  document.addEventListener('click',function(e){if(e.target.closest('.mc-open-jarvis'))setOpen(true)});
  $('mcJarvisClose').addEventListener('click',function(){setOpen(false)});

  // The old platform-mission pipeline (approve mission, execution, PR/merge/verify/rollback panels) is
  // retired from Mission Control (step 3b): platform changes go through the development workflow,
  // client work through Orca. Its buttons are hidden; the server-side machinery goes in a later clean-up.
  var RETIRED_POSTS=['/mission-control/operating-console/action','/mission-control/operating-console/workflow','/mission-control/execution',
    '/mission-control/github-execution','/mission-control/github-merge','/mission-control/rollback','/mission-control/verification'];
  var RETIRED_SECTIONS=['executions','execution','workflows','projects','board','deployments'];
  var INSIGHTS=['organisation','memory','architecture','lineage'];
  function retired(b){var t=String(b.target||'');
    if(b.action_type==='post'||b.action_type==='post_secondary')return RETIRED_POSTS.some(function(r){return t.indexOf(r)===0});
    return b.action_type==='show_section'&&RETIRED_SECTIONS.indexOf(t)>=0}
  function buttonsHtml(meta,index){var all=(meta&&meta.action_buttons)||[];
    var list=all.map(function(b,i){return {b:b,i:i}}).filter(function(x){return !retired(x.b)});
    var note=list.length<all.length?'<p class="mc-empty">Changes to this platform now go through the development workflow '+
      '(pull requests you review); client work goes to the AI team (Orca).</p>':'';
    return note+(list.length?'<div class="mc-actions">'+list.map(function(x){var b=x.b,i=x.i;var primary=b.action_type==='post'||(b.action_type==='function'&&/Orca|^Open the map|^Make a map/.test(b.label||''));
      return '<button type="button" class="mc-btn '+(primary?'':'secondary')+'" data-jarvis-msg="'+index+'" data-jarvis-btn="'+i+'">'+esc(b.label||'Continue')+'</button>'}).join('')+'</div>':'')}
  function render(){
    var box=$('mcConvo');
    if(!convo.messages.length){box.innerHTML='<li class="mc-empty">Ask a question, or describe what you want done. For customer-app work, name the app, for example “In the demo app, add a contact page”.</li>';return}
    box.innerHTML=convo.messages.map(function(m,i){return '<li class="mc-msg '+(m.role==='founder'?'me':'jarvis')+(m.error?' error':'')+'">'+esc(m.text)+(m.role==='jarvis'?buttonsHtml(m.meta,i):'')+'</li>'}).join('')+
      (busy?'<li class="mc-msg jarvis mc-empty">Jarvis is thinking…</li>':'');
    box.scrollTop=box.scrollHeight;
  }
  function add(role,text,meta,error){convo.messages.push({role:role,text:String(text||''),meta:meta||null,error:!!error});
    if(convo.messages.length>MAX)convo.messages=convo.messages.slice(-MAX);save(convo);render()}
  function reply(data,fallback){return (data&&(data.board_room_response||data.executive_summary||data.message||data.next_step))||fallback}

  async function send(text){
    if(busy||!text.trim())return;
    var history=convo.messages.slice(-8).map(function(m){return {role:m.role,text:m.text}});
    add('founder',text);busy=true;render();$('mcJarvisSend').disabled=true;
    try{var data=await MC.post('/mission-control/operating-console/chat',{message:text,conversation_id:convo.id,conversation_history:history});
      add('jarvis',reply(data,'Jarvis could not prepare a response.'),data.action_metadata||null)}
    catch(e){add('jarvis','Jarvis is unavailable right now: '+e.message,null,true)}
    finally{busy=false;$('mcJarvisSend').disabled=false;render()}
  }
  $('mcComposer').addEventListener('submit',function(e){e.preventDefault();var input=$('mcJarvisInput');var text=input.value;input.value='';send(text)});
  $('mcJarvisInput').addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('mcComposer').requestSubmit()}});

  async function runButton(b,el){
    var payload=b.payload||{};
    if(b.action_type==='function'){if(typeof window[b.target]==='function'&&FUNCTIONS.indexOf(b.target)>=0)window[b.target](payload);
      else add('jarvis','That step is no longer available in Mission Control.',null,true);return}
    if(b.action_type==='show_section'){
      if(INSIGHTS.indexOf(b.target)>=0){window.location.href='/mission-control/insights/'+b.target;return}
      if(b.target==='home'||b.target==='company'||b.target==='settings'||b.target==='customers'||b.target==='clients'){location.hash='#'+b.target;return}
      add('jarvis','That screen was part of the retired classic page.',null,true);return}
    if(b.action_type==='copy'){try{await navigator.clipboard.writeText(typeof payload==='string'?payload:JSON.stringify(payload,null,2))}catch(e){}return}
    if(b.action_type==='note'){add('jarvis',payload.text||b.label||'Noted.');return}
    if(b.action_type!=='post'&&b.action_type!=='post_secondary')return;
    if(String(b.target||'').indexOf('/mission-control/')!==0){add('jarvis','Blocked an action that pointed outside Mission Control.',null,true);return}
    el.disabled=true;
    try{var data=await MC.post(b.target,payload);add('jarvis',reply(data,'Done.'),data.action_metadata||null);if(MC.refreshHome)MC.refreshHome()}
    catch(e){add('jarvis','Mission Control could not complete that safely: '+e.message,null,true)}
    finally{el.disabled=false}
  }
  $('mcConvo').addEventListener('click',function(e){var el=e.target.closest('[data-jarvis-btn]');if(!el)return;
    var m=convo.messages[+el.dataset.jarvisMsg];var b=m&&m.meta&&(m.meta.action_buttons||[])[+el.dataset.jarvisBtn];if(b)runButton(b,el)});

  // Board Room -> Orca hand-off. v2 has no separate Orca form, so the founder confirms the app and
  // goal in a dialog and only then is the mission started; nothing starts without that click.
  window.openOrcaMission=function(payload){
    payload=payload||{};
    var goal=String(payload.goal||''),ws=String(payload.workspace||''),source=/^MISSION-[A-F0-9]{12}$/.test(String(payload.board_room_mission_id||''))?{board_room_mission_id:payload.board_room_mission_id}:null;
    if(!ws){add('jarvis','Name the customer app in your message so I can hand this to the AI team.',null,true);return}
    var ok=window.confirm('Start an AI team mission in “'+ws+'”?\n\n'+goal+'\n\nThe team plans it first; you decide about test runs before anything runs.');
    if(!ok)return;
    MC.post('/mission-control/orca/start',{goal:goal,workspace:ws,source:source}).then(function(r){
      if(r.status!=='ok')throw new Error(r.error||'Orca refused the mission.');
      add('jarvis','Handed to the AI team. It’s in Home → All work: '+r.mission.mission_id+'.');if(MC.refreshHome)MC.refreshHome();
    }).catch(function(e){add('jarvis','Could not start the mission: '+e.message,null,true)});
  };

  // UI/UX proposals (from the UI/UX agent): same endpoints and typed approval phrases as the classic
  // Board Room. Each step that changes GitHub still needs its exact phrase. Deploy waits for hosting.
  function phrase(text,expected){var got=window.prompt(text+'\n\n'+expected);if(got!==expected){add('jarvis','The approval phrase did not match, so nothing was done.');return null}add('founder',expected);return got}
  function uiuxButtons(id){return {intent_type:'ui_ux_proposal',action_buttons:[
    {label:'Approve',action_type:'function',target:'approveUiUxChange',payload:{proposal_id:id}},
    {label:'Request Changes',action_type:'function',target:'requestUiUxIteration',payload:{proposal_id:id}},
    {label:'Reject',action_type:'post',target:'/mission-control/ui-ux-agent/reject',payload:{proposal_id:id}}]}}
  window.requestUiUxIteration=async function(payload){
    var feedback=window.prompt('What should change about this proposal?');if(!feedback||!feedback.trim())return;add('founder',feedback);
    try{var d=await MC.post('/mission-control/ui-ux-agent/iterate',{proposal_id:payload.proposal_id,feedback:feedback});
      if(d.status!=='proposed'){add('jarvis',d.error||'Could not update the proposal from that feedback.',null,true);return}
      add('jarvis','Updated proposal for '+d.target_file+':\n\n'+d.sow_markdown+'\n\nApprove, request more changes, or reject.',uiuxButtons(d.proposal_id))}
    catch(e){add('jarvis','Could not update the proposal: '+e.message,null,true)}
  };
  window.approveUiUxChange=async function(payload){
    var p=phrase('This creates a real pull request. Type the exact approval phrase to confirm:','I APPROVE GITHUB EXECUTION');if(!p)return;
    try{var d=await MC.post('/mission-control/ui-ux-agent/approve',{proposal_id:payload.proposal_id,approval_phrase:p});
      var pr=d.execution&&d.execution.status==='pull-request-created'?d.execution.pull_request_number:null;
      add('jarvis',d.message||'Could not create the pull request.',pr?{action_buttons:[{label:'Merge PR',action_type:'function',target:'mergeUiUxPullRequest',payload:{pr_number:pr}}]}:null,!pr)}
    catch(e){add('jarvis','Could not create the pull request: '+e.message,null,true)}
  };
  window.mergeUiUxPullRequest=async function(payload){
    var p=phrase('This merges PR #'+payload.pr_number+' into main. Type the exact approval phrase to confirm:','I APPROVE PR MERGE');if(!p)return;
    try{var d=await MC.post('/mission-control/github-merge/execute',{pr_number:payload.pr_number,merge_method:'squash',approval_phrase:p,live_execution:true});
      add('jarvis',d.status==='pr-merged'?'Merged PR #'+payload.pr_number+' into main.':'Could not merge PR #'+payload.pr_number+': '+(d.recommended_action||d.status||'unknown error'),null,d.status!=='pr-merged')}
    catch(e){add('jarvis','Could not merge the pull request: '+e.message,null,true)}
  };
  // Small Board Room helpers from the classic chat.
  window.addInlineNote=function(text){add('jarvis',typeof text==='string'?text:(text&&text.text)||'Noted.')};
  window.saveCurrentSession=function(){add('jarvis','Saved. This conversation is kept automatically on this computer.')};
  window.editRecommendedScope=function(payload){var input=$('mcJarvisInput');setOpen(true);
    input.value=String((payload&&(payload.scope_text||payload.scope))||'');input.focus()};
  // Codebase Map (codebase_map/jarvis.py): the same confirmation as Clients before code goes to the AI
  // provider; while the map is drawn the panel checks every 15 seconds and offers Open when it's done.
  window.openCodebaseMap=function(p){window.open('/mission-control/clients/map?id='+encodeURIComponent(p.map_id),'_blank','noopener')};
  window.startCodebaseMap=async function(p){
    try{var d=await MC.post('/mission-control/clients/detail',{client_id:p.client_id});
      if(d.error){add('jarvis',d.error,null,true);return}
      if(!d.ai_provider){add('jarvis','Choose an AI provider in Settings first.',null,true);return}
      var t=d.ai_terms,terms=t?'\n\nWhat '+t.company+'\'s terms say (read '+(t.checked||'never')+'):\n- '+t.facts.join('\n- '):'';
      var who=p.own?'This is your own code. ':'Only continue if '+d.client.name+' agreed to that. ';
      if(!window.confirm('The Codebase Cartographer will read "'+p.name+'" and draw its map (a few minutes). Nothing is changed or run outside the sandbox.\n\n'+
        'To do this, the code is sent to '+d.ai_provider+'. '+who+terms))return;
      var r=await MC.post('/mission-control/clients/run-map',{codebase_id:p.codebase_id,client_consent:true,ai_provider:d.ai_provider,terms_version:t&&t.version});
      if(r.error){add('jarvis',r.error,null,true);return}
      add('jarvis','Drawing the map of '+p.name+'. This takes a few minutes; I\'ll put an Open button here when it\'s ready.');
      var tries=0,timer=setInterval(async function(){tries++;
        try{var dd=await MC.post('/mission-control/clients/detail',{client_id:p.client_id});
          var cb=(dd.client&&dd.client.codebases||[]).filter(function(b){return b.codebase_id===p.codebase_id})[0],m=cb&&cb.map;
          if(m&&m.map_id===r.map_id&&m.status!=='running'){clearInterval(timer);
            if(m.status==='ready')add('jarvis','The map of '+p.name+' is ready.',{action_buttons:[{label:'Open the map',action_type:'function',target:'openCodebaseMap',payload:{map_id:m.map_id}}]});
            else add('jarvis','The map of '+p.name+' failed: '+(m.error||'no detail'),null,true)}}catch(e){}
        if(tries>120)clearInterval(timer)},15000)}
    catch(e){add('jarvis','Could not start the map: '+e.message,null,true)}};
  window.startPlatformMap=async function(){
    try{var r=await MC.post('/mission-control/clients/map-platform',{});if(r.status!=='ready')throw new Error(r.error||'not allowed');
      window.startCodebaseMap({client_id:r.client_id,codebase_id:r.codebase_id,name:r.name,own:true})}
    catch(e){add('jarvis','Could not set up the map of this platform: '+e.message,null,true)}};
  var FUNCTIONS=['openOrcaMission','requestUiUxIteration','approveUiUxChange','mergeUiUxPullRequest',
    'addInlineNote','saveCurrentSession','editRecommendedScope','openCodebaseMap','startCodebaseMap','startPlatformMap'];

  var wasOpen;try{wasOpen=localStorage.getItem(OPEN)}catch(e){}
  setOpen(wasOpen==='1'||(wasOpen==null&&window.innerWidth>=1200));
})();
"""
