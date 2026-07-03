from __future__ import annotations

from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard


BR_UI_02_STYLE = """
.br-shell{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;height:calc(100vh - 120px)}
.br-thread-card{display:flex;flex-direction:column;min-height:0;padding:0;overflow:hidden}.br-header{padding:18px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px;align-items:center}.br-header h2{margin:0;font-size:18px}.br-thread{flex:1;overflow:auto;padding:22px;display:flex;flex-direction:column;gap:18px;background:#050b15}.br-msg{display:grid;grid-template-columns:38px minmax(0,1fr);gap:12px;align-items:start;max-width:920px}.br-msg.user{align-self:flex-end;grid-template-columns:minmax(0,1fr) 38px}.br-avatar{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;font-weight:900;background:#13233d;color:#dbeafe;border:1px solid var(--line)}.br-msg.user .br-avatar{grid-column:2;background:linear-gradient(135deg,#f59e0b,#fef3c7);color:#111827}.br-bubble{border:1px solid var(--line);border-radius:16px;padding:14px 15px;line-height:1.5;white-space:pre-wrap;background:#091426;color:#dbeafe}.br-msg.user .br-bubble{background:#102846;border-color:#28558f}.br-actions-card{border:1px solid #6d28d9;background:#0b1628;border-radius:14px;padding:13px;margin-top:12px}.br-actions-card h3{margin:4px 0 6px;font-size:16px}.br-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.br-actions button{padding:9px 11px;border-radius:10px}.br-composer{border-top:1px solid var(--line);padding:14px;background:#07101e;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px}.br-composer textarea{min-height:64px;max-height:180px;resize:vertical}.br-advisor{height:calc(100vh - 120px);position:sticky;top:22px;overflow:auto}.br-advisor .mini{border:1px solid var(--line);background:#07101e;border-radius:12px;padding:12px;margin:10px 0}.br-list{padding-left:18px;color:#dbeafe}.br-list li{margin:6px 0}.br-hidden-modal #boardModal{display:none!important}@media(max-width:1000px){.br-shell{grid-template-columns:1fr;height:auto}.br-advisor{height:auto;position:relative}.br-msg,.br-msg.user{max-width:100%;grid-template-columns:1fr}.br-avatar{display:none}}
"""


BR_UI_02_SCRIPT = r"""
<script>
(function(){
  function byId(id){return document.getElementById(id)}
  function token(){return localStorage.getItem('mission_control_token')||''}
  function post(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()})}
  function safe(s){return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function labelFor(key){return String(key||'').split('_').map(function(x){return x.charAt(0).toUpperCase()+x.slice(1)}).join(' ')}
  function ensureBoardWorkspace(){
    var board=byId('board'); if(!board || board.dataset.brUi02==='ready') return;
    board.dataset.brUi02='ready';
    board.innerHTML="<div class='br-shell'><section class='card br-thread-card'><div class='br-header'><div><div class='brand-small'>Board Room</div><h2>Executive Conversation</h2><p class='muted'>One continuous discussion. Actions appear inline only when the Board recommends them.</p></div><button class='secondary' onclick='newBoardChat()'>New Chat</button></div><div id='brThread' class='br-thread'><div class='br-msg board'><div class='br-avatar'>AI</div><div><div class='br-bubble'>Board Room ready. Tell me what you want to review, decide, or build.</div></div></div></div><div class='br-composer'><textarea id='message' placeholder='Message the Board Room...'></textarea><button id='boardBtn' class='primary' onclick='boardRoomChat()'>Send</button></div></section><aside class='card br-advisor'><div class='brand-small'>Executive Advisor</div><h2 style='margin:6px 0 10px'>Current Signal</h2><div class='mini'><strong id='conversationMode'>General Conversation</strong><p id='modeDescription' class='muted'>No message yet.</p></div><div id='executiveDecisionCard' class='mini'><strong>Recommended Action</strong><p class='muted'>None yet. Send a message first.</p></div><div class='mini'><strong>Decisions</strong><ul id='decisionMinutes' class='br-list'><li>No decisions captured yet.</li></ul></div><div class='mini'><strong>Actions</strong><ul id='actionMinutes' class='br-list'><li>No actions captured yet.</li></ul></div><div class='mini'><strong>Knowledge</strong><ul id='knowledgeMinutes' class='br-list'><li>Important context will appear here.</li></ul></div><div id='workflowCard' class='mini'>Workflow appears only after you accept an inline recommendation.</div><p id='meetingMeta' class='muted'>No meeting yet.</p></aside></div>";
    var input=byId('message'); if(input){input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();window.boardRoomChat()}})}
  }
  function thread(){ensureBoardWorkspace();return byId('brThread')}
  function addMsg(role,text,decision){
    var box=thread(); if(!box) return;
    var div=document.createElement('div'); div.className='br-msg '+(role==='user'?'user':'board');
    var avatar=document.createElement('div'); avatar.className='br-avatar'; avatar.textContent=role==='user'?'TT':'AI';
    var wrap=document.createElement('div'); var bubble=document.createElement('div'); bubble.className='br-bubble'; bubble.textContent=text||''; wrap.appendChild(bubble);
    if(decision&&decision.primary_action){wrap.appendChild(actionCard(decision))}
    if(role==='user'){div.appendChild(wrap);div.appendChild(avatar)}else{div.appendChild(avatar);div.appendChild(wrap)}
    box.appendChild(div); box.scrollTop=box.scrollHeight;
  }
  function actionCard(decision){
    var card=document.createElement('div'); card.className='br-actions-card'; var action=decision.primary_action||{};
    var html='<div class="small">Recommended next step</div><h3>'+safe(action.label||labelFor(action.key))+'</h3><p class="muted">'+safe(decision.reason||'Board Room selected the safest next action.')+'</p><div class="br-actions">';
    if(action.requires_workflow){html+='<button class="primary" onclick="createWorkflow()">'+safe(action.label||'Create Workflow')+'</button>'}else{html+='<button class="secondary" onclick="addInlineNote(\'Continue discussion selected.\')">Continue Discussion</button>'}
    (decision.alternative_actions||[]).slice(0,3).forEach(function(a){html+='<button class="secondary" onclick="addInlineNote(\'Alternative noted: '+safe(a.label||labelFor(a.key))+'\')">'+safe(a.label||labelFor(a.key))+'</button>'});
    html+='</div>'; card.innerHTML=html; return card;
  }
  function setItems(id,items,empty){var el=byId(id);if(!el)return;el.innerHTML='';var values=(items&&items.length)?items:[empty];values.slice(0,5).forEach(function(s){var li=document.createElement('li');li.textContent=s;el.appendChild(li)})}
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
    if(!decision||!decision.primary_action){card.innerHTML='<strong>Recommended Action</strong><p class="muted">None yet. Send a message first.</p>';return;}
    var action=decision.primary_action; card.innerHTML='<strong>Recommended Action</strong><h3>'+safe(action.label||labelFor(action.key))+'</h3><p class="muted">'+safe(decision.reason||'Recommended by Executive Decision Center.')+'</p>';
  };
  window.renderWorkflowCard=function(wf){
    ensureBoardWorkspace(); var card=byId('workflowCard'); if(!card||!wf)return; card.className='mini';
    var html='<strong>'+safe(wf.title)+'</strong><br><span class="small">'+safe(wf.status)+' · '+safe(wf.workflow_id)+'</span>';
    if(wf.allowed_actions&&wf.allowed_actions.length){html+='<div class="br-actions">';wf.allowed_actions.forEach(function(a){html+='<button class="'+(a.indexOf('approve')>=0?'primary':'secondary')+'" onclick="workflowAction(\''+a+'\')">'+labelFor(a)+'</button>'});html+='</div>'}
    card.innerHTML=html; window.currentWorkflow=wf;
  };
  window.newBoardChat=function(){ensureBoardWorkspace();var box=byId('brThread');if(box)box.innerHTML='';addMsg('board','New Board Room chat started.');renderExecutiveDecision(null)};
  window.openBoardRoom=function(){ensureBoardWorkspace(); if(window.showSection) window.showSection('board')};
  window.startCommand=function(){ensureBoardWorkspace(); if(window.showSection) window.showSection('board'); var ci=byId('commandInput'); var msg=byId('message'); if(ci&&msg)msg.value=ci.value||'';};
  window.boardRoomChat=async function(){
    ensureBoardWorkspace(); var input=byId('message'); var text=(input&&input.value||'').trim(); if(!text)return; var btn=byId('boardBtn'); if(btn)btn.disabled=true;
    addMsg('user',text); input.value='';
    try{var data=await post('/mission-control/operating-console/chat',{token:token(),message:text});
      if(data.board_room_response){if(data.conversation_intelligence)renderConversationIntelligence(data.conversation_intelligence,'Meeting ID: '+data.meeting_id);renderExecutiveDecision(data.executive_decision);addMsg('board',data.board_room_response,data.executive_decision)}else{addMsg('board',JSON.stringify(data,null,2))}
    }catch(e){addMsg('board','Board Room request failed: '+e)}finally{if(btn)btn.disabled=false}
  };
  window.createWorkflow=async function(){
    ensureBoardWorkspace(); addMsg('user','Accept recommended action');
    var transcript=Array.from(document.querySelectorAll('#brThread .br-bubble')).map(function(n){return n.textContent}).join('\n');
    try{var data=await post('/mission-control/operating-console/workflow',{token:token(),action:'create-proposal',message:transcript});addMsg('board','Workflow created. Review the workflow card.');if(data.conversation_intelligence)renderConversationIntelligence(data.conversation_intelligence,'Workflow generated');if(data.executive_decision)renderExecutiveDecision(data.executive_decision);if(data.founder_workflow)renderWorkflowCard(data.founder_workflow)}catch(e){addMsg('board','Workflow request failed: '+e)}
  };
  window.workflowAction=async function(action){addMsg('user',labelFor(action));addMsg('board','Workflow action recorded: '+labelFor(action))};
  document.addEventListener('DOMContentLoaded',function(){document.body.classList.add('br-hidden-modal');ensureBoardWorkspace();});
})();
</script>
"""


def render_board_chat_dashboard() -> str:
    html = render_stable_founder_dashboard()
    html = html.replace("<button class='primary' onclick='openBoardRoom()'>♙ Board Room</button>", "<button class='primary' onclick='openBoardRoom()'>♙ Board Room</button>")
    html = html.replace("</style>", BR_UI_02_STYLE + "\n</style>")
    html = html.replace("</body>", BR_UI_02_SCRIPT + "\n</body>")
    return html
