from __future__ import annotations

from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard


BR_UI_03_STYLE = """
.br-shell{max-width:1440px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:14px;height:calc(100vh - 114px)}
.br-thread-card{display:flex;flex-direction:column;min-height:0;padding:0;overflow:hidden;border-radius:18px}.br-header{padding:18px 22px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px;align-items:center;background:linear-gradient(180deg,rgba(15,27,49,.94),rgba(8,15,29,.72))}.br-header h2{margin:0;font-size:22px}.br-status{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.br-chip{border:1px solid #263a5c;background:#081426;border-radius:999px;padding:6px 10px;color:#bdd2f4;font-size:12px}.br-chip.live:before{content:'●';color:#22c55e;margin-right:6px}.br-thread{flex:1;overflow:auto;padding:28px 34px 24px;display:flex;flex-direction:column;gap:22px;background:radial-gradient(circle at 50% 0,rgba(29,78,216,.08),transparent 28%),#050b15}.br-msg{display:grid;grid-template-columns:42px minmax(0,1fr);gap:13px;align-items:start;max-width:920px}.br-msg.user{align-self:flex-end;grid-template-columns:minmax(0,1fr) 42px;max-width:760px}.br-avatar{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;font-weight:900;background:#13233d;color:#dbeafe;border:1px solid var(--line);box-shadow:0 8px 30px rgba(0,0,0,.18)}.br-msg.user .br-avatar{grid-column:2;background:linear-gradient(135deg,#f59e0b,#fef3c7);color:#111827}.br-name{font-size:12px;font-weight:800;color:#9fb4d8;margin:0 0 6px}.br-msg.user .br-name{text-align:right}.br-bubble{border:1px solid var(--line);border-radius:18px;padding:15px 16px;line-height:1.55;white-space:pre-wrap;background:#091426;color:#e6efff;box-shadow:0 12px 34px rgba(0,0,0,.14)}.br-msg.user .br-bubble{background:#102846;border-color:#28558f;color:#f8fbff}.br-welcome{border:1px solid #273b60;border-radius:20px;padding:20px;background:linear-gradient(135deg,rgba(37,99,235,.14),rgba(124,58,237,.10));max-width:850px}.br-welcome h3{margin:0 0 10px;font-size:22px}.br-starters{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}.br-starters button{border:1px solid #314a74;background:#0b1a2f;color:#dbeafe;border-radius:999px;padding:9px 12px;font-weight:750}.br-actions-card{border:1px solid #7c3aed;background:linear-gradient(180deg,#111a31,#0a1324);border-radius:16px;padding:14px;margin-top:12px;box-shadow:0 0 0 1px rgba(124,58,237,.12),0 20px 44px rgba(0,0,0,.22)}.br-actions-card h3{margin:4px 0 6px;font-size:17px}.br-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:11px}.br-actions button{padding:9px 12px;border-radius:11px}.br-composer{border-top:1px solid var(--line);padding:14px;background:#07101e;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px}.br-composer textarea{min-height:58px;max-height:180px;resize:vertical;border-radius:16px;padding:15px}.br-composer .primary{min-width:74px;border-radius:16px}.br-advisor{height:calc(100vh - 114px);position:sticky;top:22px;overflow:auto;border-radius:18px}.br-advisor h2{font-size:18px;margin:4px 0 12px}.br-brief{display:grid;gap:9px}.br-mini{border:1px solid var(--line);background:#07101e;border-radius:14px;padding:12px}.br-mini strong{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#93c5fd;margin-bottom:5px}.br-mini .value{font-weight:850;color:#f8fbff}.br-list{padding-left:18px;color:#dbeafe;margin:6px 0 0}.br-list li{margin:5px 0}.br-thinking{opacity:.8}.br-thinking .br-bubble:after{content:'  ● ● ●';letter-spacing:2px;color:#93c5fd;animation:brpulse 1s infinite}@keyframes brpulse{50%{opacity:.35}}.br-hidden-modal #boardModal{display:none!important}@media(max-width:1100px){.br-shell{grid-template-columns:1fr;height:auto}.br-advisor{height:auto;position:relative}.br-msg,.br-msg.user{max-width:100%;grid-template-columns:1fr}.br-avatar{display:none}.br-msg.user .br-name{text-align:left}.br-thread{padding:20px}}
"""


BR_UI_03_SCRIPT = r"""
<script>
(function(){
  function byId(id){return document.getElementById(id)}
  function token(){return localStorage.getItem('mission_control_token')||''}
  function post(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()})}
  function safe(s){return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function labelFor(key){return String(key||'').split('_').map(function(x){return x.charAt(0).toUpperCase()+x.slice(1)}).join(' ')}
  function ensureBoardWorkspace(){
    var board=byId('board'); if(!board || board.dataset.brUi03==='ready') return;
    board.dataset.brUi03='ready';
    board.innerHTML="<div class='br-shell'><section class='card br-thread-card'><div class='br-header'><div><div class='brand-small'>Board Room</div><h2>Executive Workspace</h2><p class='muted'>A CEO-grade conversation for strategy, architecture, governance, and execution.</p><div class='br-status'><span class='br-chip live'>Runtime Constitution loaded</span><span class='br-chip'>Founder approval enforced</span><span class='br-chip'>Production-safe mode</span></div></div><button class='secondary' onclick='newBoardChat()'>New Chat</button></div><div id='brThread' class='br-thread'></div><div class='br-composer'><textarea id='message' placeholder='Message the Board Room...'></textarea><button id='boardBtn' class='primary' onclick='boardRoomChat()'>Send</button></div></section><aside class='card br-advisor'><div class='brand-small'>Executive Brief</div><h2>Live Signal</h2><div class='br-brief'><div class='br-mini'><strong>Intent</strong><div id='conversationMode' class='value'>General Conversation</div><p id='modeDescription' class='muted'>No message yet.</p></div><div id='executiveDecisionCard' class='br-mini'><strong>Recommended Action</strong><div class='value'>None yet</div><p class='muted'>Send a message first.</p></div><div class='br-mini'><strong>Decisions</strong><ul id='decisionMinutes' class='br-list'><li>No decisions captured yet.</li></ul></div><div class='br-mini'><strong>Actions</strong><ul id='actionMinutes' class='br-list'><li>No actions captured yet.</li></ul></div><div class='br-mini'><strong>Knowledge</strong><ul id='knowledgeMinutes' class='br-list'><li>Important context will appear here.</li></ul></div><div id='workflowCard' class='br-mini'><strong>Current Mission</strong><div class='value'>None</div><p class='muted'>Workflow appears only after you accept an inline recommendation.</p></div><p id='meetingMeta' class='muted'>No meeting yet.</p></div></aside></div>";
    renderWelcome();
    var input=byId('message'); if(input){input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();window.boardRoomChat()}})}
  }
  function thread(){ensureBoardWorkspace();return byId('brThread')}
  function renderWelcome(){
    var box=byId('brThread'); if(!box) return;
    box.innerHTML="<div class='br-welcome'><h3>Welcome back, Toni.</h3><p class='muted'>I can help review architecture, prioritize missions, prepare governance-safe proposals, audit the repository, or guide product strategy. What would you like to accomplish today?</p><div class='br-starters'><button onclick='useStarter(\'Review Mission Control architecture and recommend the next engineering mission.\')'>Review architecture</button><button onclick='useStarter(\'Identify technical debt and recommend a safe implementation plan.\')'>Find technical debt</button><button onclick='useStarter(\'Create an engineering proposal for the next highest-impact mission.\')'>Create proposal</button></div></div>";
  }
  function addMsg(role,text,decision){
    var box=thread(); if(!box) return;
    var div=document.createElement('div'); div.className='br-msg '+(role==='user'?'user':'board');
    var avatar=document.createElement('div'); avatar.className='br-avatar'; avatar.textContent=role==='user'?'TT':'AI';
    var wrap=document.createElement('div'); var name=document.createElement('div'); name.className='br-name'; name.textContent=role==='user'?'You':'Board Room'; var bubble=document.createElement('div'); bubble.className='br-bubble'; bubble.textContent=text||''; wrap.appendChild(name); wrap.appendChild(bubble);
    if(decision&&decision.primary_action){wrap.appendChild(actionCard(decision))}
    if(role==='user'){div.appendChild(wrap);div.appendChild(avatar)}else{div.appendChild(avatar);div.appendChild(wrap)}
    box.appendChild(div); box.scrollTop=box.scrollHeight; return div;
  }
  function addThinking(){return addMsg('board','Analyzing request… reviewing Constitution, current context, and safest next action.',null)}
  function actionCard(decision){
    var card=document.createElement('div'); card.className='br-actions-card'; var action=decision.primary_action||{};
    var html='<div class="small">Governance-aware recommendation</div><h3>'+safe(action.label||labelFor(action.key))+'</h3><p class="muted">'+safe(decision.reason||'Board Room selected the safest next action.')+'</p><div class="br-actions">';
    if(action.requires_workflow){html+='<button class="primary" onclick="createWorkflow()">'+safe(action.label||'Create Workflow')+'</button>'}else{html+='<button class="secondary" onclick="addInlineNote(\'Continue discussion selected.\')">Continue Discussion</button>'}
    (decision.alternative_actions||[]).slice(0,3).forEach(function(a){html+='<button class="secondary" onclick="addInlineNote(\'Alternative noted: '+safe(a.label||labelFor(a.key))+'\')">'+safe(a.label||labelFor(a.key))+'</button>'});
    html+='</div>'; card.innerHTML=html; return card;
  }
  function setItems(id,items,empty){var el=byId(id);if(!el)return;el.innerHTML='';var values=(items&&items.length)?items:[empty];values.slice(0,5).forEach(function(s){var li=document.createElement('li');li.textContent=s;el.appendChild(li)})}
  window.useStarter=function(text){var msg=byId('message'); if(msg){msg.value=text;msg.focus()}};
  window.addInlineNote=function(text){addMsg('board',text)};
  window.renderConversationIntelligence=function(ci,meeting){
    if(!ci)return;ensureBoardWorkspace();
    var mode=byId('conversationMode');if(mode)mode.textContent=ci.mode||'General Conversation';
    var desc=byId('modeDescription');if(desc)desc.textContent=ci.recommended_next_action||'Review conversation.';
    setItems('decisionMinutes',ci.decisions,'No decisions captured yet.');
    setItems('actionMinutes',ci.actions,'No actions captured yet.');
    setItems('knowledgeMinutes',ci.knowledge,'Important context will appear here.');
    var meta=byId('meetingMeta');if(meta)meta.textContent=meeting||'No meeting yet.';
  };
  window.renderExecutiveDecision=function(decision){
    ensureBoardWorkspace(); var card=byId('executiveDecisionCard'); if(!card)return;
    if(!decision||!decision.primary_action){card.innerHTML='<strong>Recommended Action</strong><div class="value">None yet</div><p class="muted">Send a message first.</p>';return;}
    var action=decision.primary_action; card.innerHTML='<strong>Recommended Action</strong><div class="value">'+safe(action.label||labelFor(action.key))+'</div><p class="muted">'+safe(decision.reason||'Recommended by Executive Decision Center.')+'</p>';
  };
  window.renderWorkflowCard=function(wf){
    ensureBoardWorkspace(); var card=byId('workflowCard'); if(!card||!wf)return;
    var html='<strong>Current Mission</strong><div class="value">'+safe(wf.title)+'</div><p class="muted">'+safe(wf.status)+' · '+safe(wf.workflow_id)+'</p>';
    if(wf.allowed_actions&&wf.allowed_actions.length){html+='<div class="br-actions">';wf.allowed_actions.forEach(function(a){html+='<button class="'+(a.indexOf('approve')>=0?'primary':'secondary')+'" onclick="workflowAction(\''+a+'\')">'+labelFor(a)+'</button>'});html+='</div>'}
    card.innerHTML=html; window.currentWorkflow=wf;
  };
  window.newBoardChat=function(){ensureBoardWorkspace();renderWelcome();renderExecutiveDecision(null);setItems('decisionMinutes',null,'No decisions captured yet.');setItems('actionMinutes',null,'No actions captured yet.');setItems('knowledgeMinutes',null,'Important context will appear here.')};
  window.openBoardRoom=function(){ensureBoardWorkspace(); if(window.showSection) window.showSection('board')};
  window.startCommand=function(){ensureBoardWorkspace(); if(window.showSection) window.showSection('board'); var ci=byId('commandInput'); var msg=byId('message'); if(ci&&msg)msg.value=ci.value||'';};
  window.boardRoomChat=async function(){
    ensureBoardWorkspace(); var input=byId('message'); var text=(input&&input.value||'').trim(); if(!text)return; var btn=byId('boardBtn'); if(btn)btn.disabled=true;
    var box=thread(); if(box&&box.querySelector('.br-welcome'))box.innerHTML=''; addMsg('user',text); input.value=''; var thinking=addThinking(); if(thinking)thinking.classList.add('br-thinking');
    try{var data=await post('/mission-control/operating-console/chat',{token:token(),message:text}); if(thinking)thinking.remove();
      if(data.board_room_response){if(data.conversation_intelligence)renderConversationIntelligence(data.conversation_intelligence,'Meeting ID: '+data.meeting_id);renderExecutiveDecision(data.executive_decision);addMsg('board',data.board_room_response,data.executive_decision)}else{addMsg('board',JSON.stringify(data,null,2))}
    }catch(e){if(thinking)thinking.remove();addMsg('board','Board Room request failed: '+e)}finally{if(btn)btn.disabled=false; if(input)input.focus()}
  };
  window.createWorkflow=async function(){
    ensureBoardWorkspace(); addMsg('user','Accept recommended action'); var thinking=addThinking(); if(thinking)thinking.classList.add('br-thinking');
    var transcript=Array.from(document.querySelectorAll('#brThread .br-bubble')).map(function(n){return n.textContent}).join('\n');
    try{var data=await post('/mission-control/operating-console/workflow',{token:token(),action:'create-proposal',message:transcript}); if(thinking)thinking.remove(); addMsg('board','Workflow created. Review the Current Mission card in the Executive Brief.');if(data.conversation_intelligence)renderConversationIntelligence(data.conversation_intelligence,'Workflow generated');if(data.executive_decision)renderExecutiveDecision(data.executive_decision);if(data.founder_workflow)renderWorkflowCard(data.founder_workflow)}catch(e){if(thinking)thinking.remove();addMsg('board','Workflow request failed: '+e)}
  };
  window.workflowAction=async function(action){addMsg('user',labelFor(action));addMsg('board','Workflow action recorded: '+labelFor(action)+'. Backend advancement will remain governed by the existing Founder Workflow service.')};
  document.addEventListener('DOMContentLoaded',function(){document.body.classList.add('br-hidden-modal');ensureBoardWorkspace();});
})();
</script>
"""


def render_board_chat_dashboard() -> str:
    html = render_stable_founder_dashboard()
    html = html.replace("</style>", BR_UI_03_STYLE + "\n</style>")
    html = html.replace("</body>", BR_UI_03_SCRIPT + "\n</body>")
    return html
