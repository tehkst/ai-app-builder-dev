from __future__ import annotations


FOUNDER_DECISION_STYLE = """
.br-advisor{width:auto}.fd-empty{padding:18px;border:1px dashed #263a5c;border-radius:8px;color:#94a3b8}
.fd-card{border:1px solid #263a5c;background:#07101e;border-radius:8px;padding:14px;display:grid;gap:9px}
.fd-card h3{margin:0;font-size:15px}.fd-card p{margin:0;line-height:1.42}.fd-card .fd-state{color:#93c5fd;font-size:11px;text-transform:uppercase;font-weight:800}
.fd-actions{display:flex;gap:7px;flex-wrap:wrap}.fd-actions button{padding:7px 9px;border-radius:7px;font-size:12px}
.fd-choice{display:grid;gap:6px}.fd-choice button{text-align:left}.fd-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.fd-risk-low{border-left:3px solid #22c55e}.fd-risk-medium{border-left:3px solid #f59e0b}.fd-risk-high{border-left:3px solid #ef4444}
.fd-toggle{display:inline-flex}.fd-feedback{min-height:16px;color:#93c5fd;font-size:12px}
.fd-progress{display:flex;justify-content:space-between;gap:8px;align-items:center}.fd-summary-counts{display:flex;gap:7px;flex-wrap:wrap}.fd-count{border:1px solid #263a5c;border-radius:999px;padding:4px 7px;color:#bdd2f4;font-size:11px}
.br-inline-decision{border-top:1px solid #263a5c;margin-top:12px;padding-top:12px}.br-inline-decision p{margin:0 0 9px}.br-inline-options{display:flex;gap:7px;flex-wrap:wrap}.br-inline-options button{padding:8px 10px;border-radius:8px}
.br-shell.fd-brief-collapsed{grid-template-columns:minmax(0,1fr)}.br-shell.fd-brief-collapsed .br-advisor{display:none}
.fd-technical summary{cursor:pointer;color:#93c5fd}.fd-technical div{padding-top:8px;color:#94a3b8;font-size:12px}
.fd-close{display:none}
@media(max-width:1100px){.fd-toggle{display:inline-flex}.br-advisor{display:none}.br-advisor.fd-open{display:block}}
@media(max-width:640px){.br-advisor.fd-open{position:fixed;inset:8px;z-index:1000;height:auto;background:#07101e}.fd-close{display:block;position:sticky;top:0;z-index:2;margin-left:auto}.fd-pair{grid-template-columns:1fr}}
"""


FOUNDER_DECISION_SCRIPT = r"""
<script>
(function(){
  var current=null,inFlight=false;
  function id(x){return document.getElementById(x)}
  function safe(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function token(){return localStorage.getItem('mission_control_token')||''}
  function conversationId(){return localStorage.getItem('br_ui_active_session_id')||''}
  async function post(url,body){var response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});var data=await response.json();if(!response.ok||data.status==='conflict'||data.status==='unauthorized'||data.status==='not-found'){throw new Error(data.error||data.message||'The decision could not be updated.')}return data}
  function button(label,action,target,value,primary){return '<button class="'+(primary?'primary':'secondary')+'" data-fd-action="'+safe(action)+'" data-fd-target="'+safe(target||'')+'" data-fd-value="'+safe(value||'')+'">'+safe(label)+'</button>'}
  function card(title,body,klass){return '<section class="fd-card '+(klass||'')+'"><h3>'+safe(title)+'</h3>'+body+'</section>'}
  function recommendation(value){
    if(!value||!value.statement)return'';
    return card('Current recommendation','<div class="fd-state">'+safe(value.state||'proposed')+'</div><p><strong>'+safe(value.statement)+'</strong></p><p class="muted">'+safe(value.rationale||'')+'</p>');
  }
  function progress(state){
    var items=state.assumptions||[],confirmed=items.filter(function(item){return ['confirmed','changed'].indexOf(item.state)>=0}).length,remaining=items.filter(function(item){return item.state==='proposed'}).length;
    return card('Decision progress','<div class="fd-progress"><strong>'+confirmed+' confirmed</strong><span class="muted">'+remaining+' remaining</span></div><div class="fd-summary-counts"><span class="fd-count">'+confirmed+' assumptions confirmed</span><span class="fd-count">'+(state.alternatives||[]).length+' alternatives available</span><span class="fd-count">'+(state.risks||[]).filter(function(item){return item.state==='open'}).length+' risk open</span></div>');
  }
  function activeDecision(state){
    var request=state.decision_request;if(!request||request.state!=='open')return'';
    var item=(state.assumptions||[]).find(function(value){return value.id===request.assumption_id})||{};
    var choices=(request.options||[]).map(function(option){return button(option,'change_assumption',request.assumption_id,option,false)}).join('');
    choices+=button("Use Jarvis's recommendation",'confirm_assumption',request.assumption_id,'',true)+button('Why?','explain_assumption',request.assumption_id)+button('Skip for now','defer_decision');
    return card('Current decision','<p><strong>'+safe(request.question)+'</strong></p><p class="muted">'+safe(item.statement||request.reason)+'</p><div class="fd-actions">'+choices+'</div>');
  }
  function confirmed(items){
    var values=(items||[]).filter(function(item){return ['confirmed','changed','rejected'].indexOf(item.state)>=0});if(!values.length)return'';
    return '<details class="fd-technical"><summary>'+values.length+' confirmed decision'+(values.length===1?'':'s')+'</summary><div>'+values.map(function(item){return '<p>'+safe(item.statement)+' <button class="secondary" data-fd-action="change_assumption" data-fd-target="'+safe(item.id)+'" data-fd-value="'+safe((item.options||[])[0]||item.statement)+'">Edit</button></p>'}).join('')+'</div></details>';
  }
  function keyRisk(items){
    var item=(items||[]).find(function(value){return value.state==='open'})||(items||[])[0];if(!item)return'';
    return card('Key risk','<div class="fd-state">'+safe(item.level)+'</div><p>'+safe(item.statement)+'</p><p class="muted">'+safe(item.mitigation)+'</p>','fd-risk-'+safe(item.level));
  }
  function mission(items,ready){
    if(!items||!items.length)return'';
    var item=items[0],meta=item.governed_actions||{},buttons=ready?(meta.action_buttons||[]).map(function(action,index){return '<button class="'+(index===0?'primary':'secondary')+'" data-fd-mission="'+index+'">'+safe(action.label)+'</button>'}).join(''):'';
    return card('Mission readiness','<div class="fd-state">'+(ready?'READY FOR REVIEW':'CLARIFYING')+'</div><p><strong>'+safe(item.title)+'</strong></p><p class="muted">'+(ready?safe(item.scope):'Jarvis is refining the scope one material decision at a time.')+'</p>'+(buttons?'<div class="fd-actions">'+buttons+'</div>':''));
  }
  function challenge(value){
    if(!value)return'';
    return card('Recommendation challenge','<p>'+safe(value.counterargument)+'</p><p class="muted"><strong>What would change the decision:</strong> '+safe(value.decision_changing_condition)+'</p><div class="fd-state">Revised confidence: '+safe(value.revised_confidence)+'</div>');
  }
  function render(state){
    current=state||null;var brief=document.querySelector('.br-brief');if(!brief)return;
    if(!current){brief.innerHTML='<div class="fd-empty">Start a conversation to build a decision-ready executive brief.</div>';return}
    brief.innerHTML=recommendation(current.recommendation)+progress(current)+activeDecision(current)+confirmed(current.assumptions)+keyRisk(current.risks)+mission(current.mission_proposals,!(current.decision_request&&current.decision_request.state==='open'))+challenge(current.challenge)+'<div id="fdFeedback" class="fd-feedback" role="status" aria-live="polite"></div><details class="fd-technical"><summary>More context</summary><div>'+safe((current.alternatives||[]).length)+' alternatives · '+safe((current.actions||[]).length)+' prepared actions</div></details><details class="fd-technical"><summary>Technical details</summary><div>Contract '+safe(current.contract)+' · version '+safe(current.version)+' · updated '+safe(current.updated_at)+'</div></details>';
    brief.querySelectorAll('[data-fd-action]').forEach(function(el){el.onclick=function(){apply(el.dataset.fdAction,el.dataset.fdTarget,el.dataset.fdValue,el)}});
    brief.querySelectorAll('[data-fd-mission]').forEach(function(el){el.onclick=function(){runMission(Number(el.dataset.fdMission),el)}});
  }
  function choiceLabel(action,value){if(value)return value;return {'confirm_assumption':"Use Jarvis's recommendation",'challenge_recommendation':'Challenge the recommendation','show_alternatives':'Show alternatives','defer_decision':'Skip for now','explain_assumption':'Why does this matter?'}[action]||action.replace(/_/g,' ')}
  async function apply(action,target,value,el,source,messageId){
    if(inFlight||!current)return;inFlight=true;el.disabled=true;var feedback=id('fdFeedback'),label=choiceLabel(action,value),pending=null;
    if(window.addFounderDecisionChoice)window.addFounderDecisionChoice(label);if(window.beginFounderDecisionContinuation)pending=window.beginFounderDecisionContinuation();
    try{var data=await post('/mission-control/decision-experience/action',{token:token(),conversation_id:current.conversation_id,expected_version:current.version,action:action,target_id:target,value:value,source_message_id:messageId||'',interaction_source:source||'executive_brief',action_id:current.conversation_id+':'+current.version+':'+action+':'+target+':'+value});document.querySelectorAll('.br-inline-decision').forEach(function(node){node.remove()});render(data.decision_experience);if(window.completeFounderDecisionContinuation)await window.completeFounderDecisionContinuation(pending,(data.continuation||{}).message||'I have updated the recommendation.',data.decision_experience)}
    catch(error){if(pending&&pending.parentNode)pending.remove();if(feedback)feedback.textContent='Your choice is still visible. '+error.message+' Retry when ready.'}
    finally{inFlight=false;if(el&&el.isConnected)el.disabled=false}
  }
  function inlineControls(state,messageId){
    var request=state&&state.decision_request;if(!request||request.state!=='open')return null;var box=document.createElement('div');box.className='br-inline-decision';box.setAttribute('role','group');box.setAttribute('aria-label','Current material decision');box.innerHTML='<p><strong>'+safe(request.question)+'</strong></p><div class="br-inline-options"></div>';var row=box.querySelector('.br-inline-options');(request.options||[]).forEach(function(option){var el=document.createElement('button');el.className='secondary';el.textContent=option;el.onclick=function(){apply('change_assumption',request.assumption_id,option,el,'chat',messageId)};row.appendChild(el)});[["Use Jarvis's recommendation",'confirm_assumption'],['Why?','explain_assumption'],['Skip for now','defer_decision']].forEach(function(pair){var el=document.createElement('button');el.className=pair[1]==='confirm_assumption'?'primary':'secondary';el.textContent=pair[0];el.onclick=function(){apply(pair[1],request.assumption_id,'',el,'chat',messageId)};row.appendChild(el)});return box
  }
  window.attachFounderDecisionControls=function(message,state){if(!message||!state)return;var content=message.querySelector('.br-content'),control=inlineControls(state,message.dataset.messageId);if(content&&control)content.appendChild(control)};
  async function runMission(index,el){
    if(inFlight||!current)return;var proposal=(current.mission_proposals||[])[0],meta=proposal&&proposal.governed_actions,action=meta&&(meta.action_buttons||[])[index];if(!action)return;
    inFlight=true;el.disabled=true;try{var body=Object.assign({token:token()},action.payload||{});var data=await post(action.target,body);if(window.acceptDurableMissionResult&&data.workflow_run_id)window.acceptDurableMissionResult(data);var feedback=id('fdFeedback');if(feedback)feedback.textContent=data.board_room_response||data.message||'Mission action completed.'}catch(error){var feedback=id('fdFeedback');if(feedback)feedback.textContent=error.message}finally{inFlight=false;if(el&&el.isConnected)el.disabled=false}
  }
  window.renderFounderDecisionExperience=render;
  window.loadFounderDecisionState=async function(cid){if(!cid){render(null);return}try{var data=await post('/mission-control/decision-experience/state',{token:token(),conversation_id:cid});render(data.decision_experience);document.querySelectorAll('.br-inline-decision').forEach(function(node){node.remove()});var messages=document.querySelectorAll('#brThread .br-msg.board');var last=messages.length?messages[messages.length-1]:null;if(last)window.attachFounderDecisionControls(last,data.decision_experience)}catch(error){render(null)}};
  window.toggleFounderBrief=function(){var panel=document.querySelector('.br-advisor'),shell=document.querySelector('.br-shell');if(!panel||!shell)return;if(window.matchMedia('(max-width:1100px)').matches){panel.classList.toggle('fd-open')}else{shell.classList.toggle('fd-brief-collapsed')}};
})();
</script>
"""
