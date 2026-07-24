from __future__ import annotations


FOUNDER_DECISION_STYLE = """
.br-advisor{width:auto}.fd-empty{padding:18px;border:1px dashed #263a5c;border-radius:8px;color:#94a3b8}
.fd-card{border:1px solid #263a5c;background:#07101e;border-radius:8px;padding:14px;display:grid;gap:9px}
.fd-card h3{margin:0;font-size:15px}.fd-card p{margin:0;line-height:1.42}.fd-card .fd-state{color:#93c5fd;font-size:11px;text-transform:uppercase;font-weight:800}
.fd-actions{display:flex;gap:7px;flex-wrap:wrap}.fd-actions button{padding:7px 9px;border-radius:7px;font-size:12px}
.fd-choice{display:grid;gap:6px}.fd-choice button{text-align:left}.fd-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.fd-risk-low{border-left:3px solid #22c55e}.fd-risk-medium{border-left:3px solid #f59e0b}.fd-risk-high{border-left:3px solid #ef4444}
.fd-toggle{display:inline-flex}.fd-feedback{min-height:16px;color:#93c5fd;font-size:12px}
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
    var body='<div class="fd-state">'+safe(value.state||'proposed')+'</div><p><strong>'+safe(value.statement)+'</strong></p><p class="muted">'+safe(value.rationale||'')+'</p><div class="fd-actions">'+button('Accept','accept_recommendation','', '',true)+button('Change','change_recommendation')+button('Challenge','challenge_recommendation')+button('Show alternatives','show_alternatives')+button('Defer','defer_decision')+'</div>';
    return card('Recommendation',body);
  }
  function assumptions(items,request){
    if(!items||!items.length)return'';
    var body=items.map(function(item){var choices=(item.options||[]).map(function(option){return button(option,'change_assumption',item.id,option,false)}).join('');return '<div class="fd-choice"><div class="fd-state">'+safe(item.state)+' · '+safe(item.confidence)+' confidence</div><p>'+safe(item.statement)+'</p>'+(item.explanation?'<p class="muted">'+safe(item.explanation)+'</p>':'')+(request&&request.assumption_id===item.id?'<p class="muted">'+safe(request.reason)+'</p><div class="fd-actions">'+choices+'</div>':'')+'<div class="fd-actions">'+button('Confirm','confirm_assumption',item.id,'',true)+button('Change','change_assumption',item.id,(item.options||[])[0]||'')+button('Reject','reject_assumption',item.id)+button('Why?','explain_assumption',item.id)+'</div></div>'}).join('');
    return card('Working assumptions',body);
  }
  function alternatives(items,tradeoffs){
    if(!items||!items.length)return'';
    var body=items.map(function(item){return '<div class="fd-choice"><p><strong>'+safe(item.label)+'</strong></p><p class="muted">'+safe(item.benefit)+' '+safe(item.cost)+'</p>'+button('Choose this option','select_alternative',item.id)+'</div>'}).join('');
    if(tradeoffs&&tradeoffs.length)body+='<div class="fd-pair"><p><strong>Gain</strong><br>'+safe(tradeoffs[0].gain)+'</p><p><strong>Give up</strong><br>'+safe(tradeoffs[0].sacrifice)+'</p></div>';
    return card('Alternatives and trade-off',body);
  }
  function actions(items){
    if(!items||!items.length)return'';
    return card('Next actions',items.map(function(item){return '<div class="fd-choice"><div class="fd-state">'+safe(item.state)+' · Owner: '+safe(item.owner)+'</div><p>'+safe(item.title)+'</p><div class="fd-actions">'+button('Approve','approve_action',item.id,'',true)+button('Assign Jarvis','assign_ai',item.id)+button('Assign founder','assign_founder',item.id)+button('Edit','edit_action',item.id,item.title)+button('Defer','defer_action',item.id)+button('Reject','reject_action',item.id)+button('Complete','complete_action',item.id)+'</div></div>'}).join(''));
  }
  function risks(items){
    if(!items||!items.length)return'';
    return items.map(function(item){return card('Risk · '+item.level,'<div class="fd-state">'+safe(item.state)+'</div><p>'+safe(item.statement)+'</p><p class="muted">'+safe(item.mitigation)+'</p><div class="fd-actions">'+button('Accept risk','accept_risk',item.id)+button('Mitigate','mitigate_risk',item.id,'',true)+'</div>','fd-risk-'+safe(item.level))}).join('');
  }
  function mission(items){
    if(!items||!items.length)return'';
    var item=items[0],meta=item.governed_actions||{},buttons=(meta.action_buttons||[]).map(function(action,index){return '<button class="'+(index===0?'primary':'secondary')+'" data-fd-mission="'+index+'">'+safe(action.label)+'</button>'}).join('');
    return card('Mission proposal','<div class="fd-state">'+safe(item.approval_state)+'</div><p><strong>'+safe(item.title)+'</strong></p><p class="muted">'+safe(item.scope)+'</p><div class="fd-actions">'+buttons+'</div>');
  }
  function challenge(value){
    if(!value)return'';
    return card('Recommendation challenge','<p>'+safe(value.counterargument)+'</p><p class="muted"><strong>What would change the decision:</strong> '+safe(value.decision_changing_condition)+'</p><div class="fd-state">Revised confidence: '+safe(value.revised_confidence)+'</div>');
  }
  function render(state){
    current=state||null;var brief=document.querySelector('.br-brief');if(!brief)return;
    if(!current){brief.innerHTML='<div class="fd-empty">Start a conversation to build a decision-ready executive brief.</div>';return}
    brief.innerHTML=recommendation(current.recommendation)+challenge(current.challenge)+assumptions(current.assumptions,current.decision_request)+alternatives(current.alternatives,current.trade_offs)+actions(current.actions)+risks(current.risks)+mission(current.mission_proposals)+'<div id="fdFeedback" class="fd-feedback" role="status" aria-live="polite"></div><details class="fd-technical"><summary>Technical details</summary><div>Contract '+safe(current.contract)+' · version '+safe(current.version)+' · updated '+safe(current.updated_at)+'</div></details>';
    brief.querySelectorAll('[data-fd-action]').forEach(function(el){el.onclick=function(){apply(el.dataset.fdAction,el.dataset.fdTarget,el.dataset.fdValue,el)}});
    brief.querySelectorAll('[data-fd-mission]').forEach(function(el){el.onclick=function(){runMission(Number(el.dataset.fdMission),el)}});
  }
  async function apply(action,target,value,el){
    if(inFlight||!current)return;inFlight=true;el.disabled=true;var feedback=id('fdFeedback');
    try{var data=await post('/mission-control/decision-experience/action',{token:token(),conversation_id:current.conversation_id,expected_version:current.version,action:action,target_id:target,value:value,action_id:current.conversation_id+':'+current.version+':'+action+':'+target});render(data.decision_experience);if(window.addFounderDecisionEvent)window.addFounderDecisionEvent('Executive Brief updated: '+action.replace(/_/g,' ')+'.')}
    catch(error){if(feedback)feedback.textContent=error.message}
    finally{inFlight=false;if(el&&el.isConnected)el.disabled=false}
  }
  async function runMission(index,el){
    if(inFlight||!current)return;var proposal=(current.mission_proposals||[])[0],meta=proposal&&proposal.governed_actions,action=meta&&(meta.action_buttons||[])[index];if(!action)return;
    inFlight=true;el.disabled=true;try{var body=Object.assign({token:token()},action.payload||{});var data=await post(action.target,body);if(window.acceptDurableMissionResult&&data.workflow_run_id)window.acceptDurableMissionResult(data);var feedback=id('fdFeedback');if(feedback)feedback.textContent=data.board_room_response||data.message||'Mission action completed.'}catch(error){var feedback=id('fdFeedback');if(feedback)feedback.textContent=error.message}finally{inFlight=false;if(el&&el.isConnected)el.disabled=false}
  }
  window.renderFounderDecisionExperience=render;
  window.loadFounderDecisionState=async function(cid){if(!cid){render(null);return}try{var data=await post('/mission-control/decision-experience/state',{token:token(),conversation_id:cid});render(data.decision_experience)}catch(error){render(null)}};
  window.toggleFounderBrief=function(){var panel=document.querySelector('.br-advisor'),shell=document.querySelector('.br-shell');if(!panel||!shell)return;if(window.matchMedia('(max-width:1100px)').matches){panel.classList.toggle('fd-open')}else{shell.classList.toggle('fd-brief-collapsed')}};
})();
</script>
"""
