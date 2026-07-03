from __future__ import annotations

from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard


BOARD_ROOM_STYLE = """
.board-chat-note{border:1px solid var(--line);background:#07101e;border-radius:12px;padding:12px;margin-bottom:12px;color:var(--muted)}
.board-chat-grid{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:14px}
.board-minutes{border:1px solid var(--line);border-radius:12px;padding:14px;background:#07101e}
.board-minutes ul{padding-left:18px;color:#dbeafe}
.board-minutes li{margin:6px 0}
.board-mode-strip{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.mode-pill{display:inline-flex;border:1px solid #334155;background:#102846;border-radius:999px;padding:6px 10px;color:#dbeafe;font-size:12px;font-weight:800}
.mission-card{border:1px solid var(--line);border-radius:12px;padding:12px;margin:14px 0;background:#0b1628}
.mission-card.ready{border-color:#6d28d9;color:#f2f7ff}
.executive-decision{border:1px solid #6d28d9;border-radius:14px;padding:12px;margin:14px 0;background:#0b1628;color:#f2f7ff}
.executive-decision .reason{color:var(--muted);font-size:13px;margin:8px 0 0}
.executive-action-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.executive-action-row button{padding:8px 10px;border-radius:10px}
.workflow-stage{display:flex;gap:7px;align-items:center;margin:5px 0;color:#dbeafe}
.workflow-stage.complete{color:#22c55e}
.workflow-stage.current{color:#fbbf24;font-weight:800}
.workflow-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.workflow-actions button{padding:8px 10px;border-radius:10px}
@media(max-width:900px){.board-chat-grid{grid-template-columns:1fr}}
"""


BOARD_ROOM_SCRIPT = r"""
<script>
(function(){
  function byId(id){return document.getElementById(id)}
  function token(){return localStorage.getItem('mission_control_token')||''}
  function post(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()})}
  function show(data){var result=byId('result');if(result)result.textContent=(typeof data==='string')?data:JSON.stringify(data,null,2)}
  function setItems(id,items,empty){var el=byId(id);if(!el)return;el.innerHTML='';var values=(items&&items.length)?items:[empty];values.slice(0,6).forEach(function(s){var li=document.createElement('li');li.textContent=s;el.appendChild(li)})}
  function labelFor(key){return String(key||'').split('_').map(function(x){return x.charAt(0).toUpperCase()+x.slice(1)}).join(' ')}
  window.renderConversationIntelligence=function(ci,meeting){
    if(!ci)return;
    var pill=byId('conversationMode');if(pill)pill.textContent=ci.mode||'General Conversation';
    var desc=byId('modeDescription');if(desc)desc.textContent=ci.recommended_next_action||'Review conversation.';
    var suggest=byId('missionSuggestion');if(suggest)suggest.textContent=ci.mission_required?'Mission suggested':'No mission suggested';
    setItems('decisionMinutes',ci.decisions,'No decisions captured yet.');
    setItems('actionMinutes',ci.actions,'No actions captured yet.');
    setItems('knowledgeMinutes',ci.knowledge,'Important context will appear here.');
    var card=byId('missionCard');
    if(card){card.className='mission-card '+(ci.mission_required?'ready':'muted');card.textContent=(ci.mission_suggestion&&ci.mission_suggestion.suggested)?'Suggested: '+ci.mission_suggestion.title:'Working note only. Do not auto-create a mission.'}
    var meta=byId('meetingMeta');if(meta)meta.textContent=meeting||'No meeting yet.';
  };
  window.renderExecutiveDecision=function(decision){
    var card=byId('executiveDecisionCard');if(!card)return;
    if(!decision||!decision.primary_action){card.className='executive-decision muted';card.innerHTML='<strong>Executive Advisor</strong><p class="reason">Send a message first. The Board Room will recommend the next action.</p>';return;}
    var action=decision.primary_action;
    var html='<strong>Executive Advisor</strong><p class="reason">Recommended next step</p><h3 style="margin:6px 0">'+(action.label||labelFor(action.key))+'</h3><p class="reason">'+(decision.reason||'Board Room selected the safest next action.')+'</p>';
    html+='<div class="executive-action-row">';
    if(action.requires_workflow){html+='<button class="primary" onclick="createWorkflow()">'+(action.label||'Create Workflow')+'</button>'}else{html+='<button class="secondary" onclick="show(\'Continue discussion selected. Type your next message and click Send.\')">Continue Discussion</button>'}
    (decision.alternative_actions||[]).slice(0,3).forEach(function(a){html+='<button class="secondary" onclick="show(\'Alternative action: '+(a.label||labelFor(a.key))+'\')">'+(a.label||labelFor(a.key))+'</button>'});
    html+='</div>';
    card.className='executive-decision ready';card.innerHTML=html;
  };
  window.renderWorkflowCard=function(wf){
    var card=byId('workflowCard');if(!card||!wf)return;
    card.className='mission-card ready';
    var html='<strong>'+wf.title+'</strong><br><span class="small">'+wf.status+' · '+wf.workflow_id+'</span>';
    if(wf.stages){html+='<div style="margin-top:10px">';wf.stages.forEach(function(s){var mark=s.state==='complete'?'✓':(s.state==='current'?'●':'○');html+='<div class="workflow-stage '+s.state+'">'+mark+' '+s.label+'</div>'});html+='</div>'}
    html+='<p class="muted">Next: '+wf.next_action+'</p>';
    if(wf.allowed_actions&&wf.allowed_actions.length){html+='<div class="workflow-actions">';wf.allowed_actions.forEach(function(a){var label=labelFor(a);html+='<button class="'+(a.indexOf('approve')>=0?'primary':'secondary')+'" onclick="workflowAction(\''+a+'\')">'+label+'</button>'});html+='</div>'}
    card.innerHTML=html;window.currentWorkflow=wf;
  };
  window.workflowAction=async function(action){
    if(!window.currentWorkflow)return;
    var target=action==='approve_mission'?'repository_audit':window.currentWorkflow.current_stage;
    show('Workflow action: '+action);
    try{var data=await post('/mission-control/founder-workflows/advance',{token:token(),workflow_id:window.currentWorkflow.workflow_id,title:window.currentWorkflow.title,workflow_type:window.currentWorkflow.workflow_type,target_stage:target,approval_status:action.indexOf('approve')>=0?'approved':'pending'});show(data);if(data.workflow)window.renderWorkflowCard(data.workflow)}catch(e){show('Workflow action failed: '+e)}
  };
  window.newBoardChat=function(){
    if(byId('message'))byId('message').value='';
    show('New Board Room chat started.');
    var wc=byId('workflowCard');if(wc){wc.className='mission-card muted';wc.textContent='Workflow card will appear only after you accept the recommended action.'}
    window.renderExecutiveDecision(null);
    if(window.openBoardRoom)window.openBoardRoom();
  };
  window.boardRoomChat=async function(){
    var btn=byId('boardBtn');if(btn)btn.disabled=true;show('Board Room is thinking...');
    try{var data=await post('/mission-control/operating-console/chat',{token:token(),message:byId('message').value});if(data.board_room_response){show(data.board_room_response+'\n\n---\nMeeting ID: '+data.meeting_id+'\nStatus: '+data.status);if(data.conversation_intelligence)window.renderConversationIntelligence(data.conversation_intelligence,'Meeting ID: '+data.meeting_id);window.renderExecutiveDecision(data.executive_decision)}else{show(data)}}catch(e){show('Board Room request failed: '+e)}finally{if(btn)btn.disabled=false}
  };
  window.createWorkflow=async function(){
    show('Creating workflow from the Board Room recommended action...');
    try{var data=await post('/mission-control/operating-console/workflow',{token:token(),action:'create-proposal',message:byId('message').value});show(data);if(data.conversation_intelligence)window.renderConversationIntelligence(data.conversation_intelligence,'Workflow generated');if(data.executive_decision)window.renderExecutiveDecision(data.executive_decision);if(data.founder_workflow)window.renderWorkflowCard(data.founder_workflow)}catch(e){show('Workflow request failed: '+e)}
  };
})();
</script>
"""


def render_board_chat_dashboard() -> str:
    html = render_stable_founder_dashboard()
    html = html.replace("<button class='primary' onclick='openBoardRoom()'>Start Discussion</button>", "<button class='primary' onclick='newBoardChat()'>New Chat</button>")
    html = html.replace("<h2>Board Room Discussion</h2><button class='secondary' onclick='closeBoardRoom()'>Close</button>", "<h2>Board Room Executive Chat</h2><div><button class='secondary' onclick='newBoardChat()'>New Chat</button> <button class='secondary' onclick='closeBoardRoom()'>Close</button></div>")
    html = html.replace("<textarea id='message' placeholder='Tell the Board Room what you want to discuss.'></textarea>", "<div class='board-chat-note'>Chat starts as normal conversation. The Board Room recommends the next action only when the intent is clear.</div><textarea id='message' placeholder='Message the Board Room...' rows='3'></textarea>")
    html = html.replace("Start Board Room Discussion", "Send")
    html = html.replace("Create Proposal From Discussion", "Recommended Action")
    html = html.replace("<h3>Board Room Response</h3><pre id='result'>Type a message and start the discussion.</pre>", "<div class='board-chat-grid'><section><div class='board-mode-strip'><span id='conversationMode' class='mode-pill'>General Conversation</span><span id='missionSuggestion' class='small'>No mission suggested</span></div><h3>Chat</h3><pre id='result'>Start a new Board Room chat.</pre></section><aside class='board-minutes'><h3>Executive Advisor</h3><p><strong>Understanding</strong></p><p id='modeDescription' class='muted'>General clarification or discussion. No execution required.</p><div id='executiveDecisionCard' class='executive-decision muted'><strong>Recommended Action</strong><p class='reason'>Send a message first. The Board Room will decide whether to continue discussion, generate a roadmap, create a proposal, or take no action.</p></div><p><strong>Decisions</strong></p><ul id='decisionMinutes'><li>No decisions captured yet.</li></ul><p><strong>Actions</strong></p><ul id='actionMinutes'><li>No actions captured yet.</li></ul><p><strong>Knowledge</strong></p><ul id='knowledgeMinutes'><li>Important context will appear here.</li></ul><div id='missionCard' class='mission-card muted'>Mission promotion will appear here only when appropriate.</div><div id='workflowCard' class='mission-card muted'>Workflow card will appear only after you accept the recommended action.</div><p id='meetingMeta' class='muted'>No meeting yet.</p></aside></div>")
    html = html.replace("</style>", BOARD_ROOM_STYLE + "\n</style>")
    html = html.replace("</body>", BOARD_ROOM_SCRIPT + "\n</body>")
    return html
