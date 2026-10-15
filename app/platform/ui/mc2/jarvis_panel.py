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

  function buttonsHtml(meta,index){var list=(meta&&meta.action_buttons)||[];
    return list.length?'<div class="mc-actions">'+list.map(function(b,i){var primary=b.action_type==='post'||(b.action_type==='function'&&/Orca/.test(b.label||''));
      return '<button type="button" class="mc-btn '+(primary?'':'secondary')+'" data-jarvis-msg="'+index+'" data-jarvis-btn="'+i+'">'+esc(b.label||'Continue')+'</button>'}).join('')+'</div>':''}
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
    if(b.action_type==='function'){if(typeof window[b.target]==='function')window[b.target](payload);else add('jarvis','That action is not available on this screen yet.',null,true);return}
    if(b.action_type==='show_section'){add('jarvis','That opens a classic Mission Control screen.',{action_buttons:[]});window.open('/mission-control/ui#'+encodeURIComponent(b.target||''),'_blank','noopener');return}
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

  var wasOpen;try{wasOpen=localStorage.getItem(OPEN)}catch(e){}
  setOpen(wasOpen==='1'||(wasOpen==null&&window.innerWidth>=1200));
})();
"""
