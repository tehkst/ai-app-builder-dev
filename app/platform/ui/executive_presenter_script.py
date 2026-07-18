from __future__ import annotations


def render_executive_presenter_script() -> str:
    return r"""<script>(function(){
function esc(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function json(value){try{return JSON.stringify(value,null,2)}catch(e){return String(value||'')}}
function humanize(value){return String(value||'').replace(/[_-]/g,' ').replace(/\b\w/g,function(c){return c.toUpperCase()})}
function missionFrom(response){return response&&(response.mission||response.active_mission||response)||{}}
function isGenericTitle(title){var text=String(title||'').toLowerCase();return !text||text.indexOf('implementation-request')>=0||text==='mission'||text==='execution mission'}
function translateStage(stage){
  var key=String(stage||'').trim();
  var map={intent_received:'Planning',requirements_clarified:'Requirements understood',scope_of_work:'Scope defined',architecture_review:'Architecture review',implementation_plan:'Engineering plan ready',validation_plan:'Validation plan ready',founder_approval_required:'Awaiting your approval',ready_for_execution:'Ready to execute',planning:'Planning',engineering:'Engineering',pr:'Pull request review',deploy:'Deployment',verify:'Verification',complete:'Complete'};
  return map[key]||humanize(key||'in progress');
}
function inferMissionTitle(response){
  var mission=missionFrom(response), title=mission.title||mission.mission_label||'';
  if(!isGenericTitle(title))return title;
  var lines=String(mission.founder_request||response.founder_request||'').split(/\n/);
  for(var i=0;i<lines.length;i++){
    var clean=lines[i].replace('Founder request:','').trim().replace(/^"|"$/g,'');
    if(/^(implement|improve|fix|add|build|create|refine)\b/i.test(clean))return clean.slice(0,120);
  }
  return mission.objective||'Mission Control improvement';
}
function nextAction(response){
  var mission=missionFrom(response);
  return mission.next_recommended_action||mission.auto_progress_next||mission.next_action||response.next_action||'Monitor progress';
}
function executiveSummary(response){
  var mission=missionFrom(response);
  if(mission.executive_summary)return mission.executive_summary;
  return 'I have prepared a mission view for '+inferMissionTitle(response)+'. Current status: '+translateStage(mission.current_stage||mission.status)+'. The next step stays inside the existing governed workflow.';
}
function progressItems(response){
  var mission=missionFrom(response), stages=mission.stages||(mission.auto_progress&&mission.auto_progress.stages)||[];
  return stages.map(function(stage){var name=stage.name||stage.stage||stage.label||'Stage';return {label:translateStage(name),completed:Boolean(stage.completed||stage.state==='auto-completed'),waiting:stage.state==='waiting-for-founder'||/approval/i.test(name)}});
}
function progressHtml(response){
  var items=progressItems(response);
  if(!items.length)return '<p class="muted">Progress will appear as soon as the mission reports stages.</p>';
  return '<div class="executive-progress">'+items.map(function(item){var mark=item.completed?'✓':(item.waiting?'!':'○'), tone=item.completed?'good':(item.waiting?'warn':'muted');return '<div class="row"><span><strong class="'+tone+'">'+esc(mark)+'</strong> '+esc(item.label)+'</span><span class="'+tone+'">'+esc(item.completed?'Complete':(item.waiting?'Needs approval':'Pending'))+'</span></div>'}).join('')+'</div>';
}
function progressLabel(value){if(value===null)return 'Not linked';if(value===undefined)return 'Unknown';return String(value)+'%'}
function recommendationHtml(value){
  var rec=value||{};
  if(typeof rec==='string')return '<p class="good">'+esc(rec)+'</p>';
  var action=rec.action||rec.recommended_action||rec.next_action||rec.summary||'Monitor progress';
  var confidence=rec.confidence||rec.confidence_level||rec.score||'Not scored';
  var reason=rec.reason||rec.blocking_reason||rec.detail||'No blocker reported.';
  return '<div class="row"><span>Recommended next action</span><span class="good">'+esc(action)+'</span></div><div class="row"><span>Confidence</span><span>'+esc(confidence)+'</span></div><div class="row"><span>Reason</span><span>'+esc(reason)+'</span></div>';
}
function detailsHtml(data,label){
  return '<details class="technical-details"><summary>'+esc(label||'View Technical Details')+'</summary><pre style="min-height:120px">'+esc(json(data))+'</pre></details>';
}
function actionButtonsHtml(response){
  var mission=missionFrom(response), action=String(nextAction(response)).toLowerCase(), buttons=[];
  if(action.indexOf('pr')>=0||action.indexOf('pull request')>=0)buttons.push(['Review PR','executions','primary']);
  else if(action.indexOf('deploy')>=0)buttons.push(['Open Deployment Panel','executions','primary']);
  else if(action.indexOf('rollback')>=0)buttons.push(['Open Rollback Panel','executions','primary']);
  else if(action.indexOf('approval')>=0||mission.approval_required)buttons.push(['Review Approval','execution','primary']);
  else buttons.push(['Open Mission Execution','execution','primary']);
  buttons.push(['Open Board Room','board','secondary']);
  return '<div class="actions">'+buttons.map(function(b){return '<button class="'+b[2]+' mission-workspace-jump" data-target="'+esc(b[1])+'">'+esc(b[0])+'</button>'}).join('')+'</div>';
}
function governanceHtml(response){
  var mission=missionFrom(response), action=String(nextAction(response)).toLowerCase(), needs=mission.approval_required||action.indexOf('approval')>=0||action.indexOf('merge')>=0||action.indexOf('deploy')>=0||action.indexOf('rollback')>=0;
  if(!needs)return '';
  var msg=action.indexOf('rollback')>=0?'Verification needs attention. Review rollback before taking action.':(action.indexOf('deploy')>=0?'Production deployment needs founder approval.':(action.indexOf('merge')>=0?'Pull request merge needs founder approval.':'Your approval is needed before this mission proceeds.'));
  return '<h3>Governance</h3><div class="proposal-box"><p>'+esc(msg)+'</p>'+actionButtonsHtml(response)+'</div>';
}
function workspaceTabsHtml(response){
  var mission=missionFrom(response), tabs=[['goal','Goal'],['context','Context'],['attachments','Attachments'],['timeline','Timeline'],['approvals','Approvals'],['engineering','Engineering'],['pr','PR'],['deployment','Deployment'],['verification','Verification'],['rollback','Rollback'],['discussion','Discussion']];
  var content={goal:'<p>'+esc(mission.objective||mission.founder_request||'Mission goal is still being clarified.')+'</p>',context:'<p>'+esc(mission.executive_summary||executiveSummary(response))+'</p>',attachments:'<p class="muted">No attachments connected to this mission yet.</p>',timeline:'<p class="muted">Timeline appears below when available.</p>',approvals:'<p>'+esc(mission.approval_required?'Founder approval is currently needed.':'No approval is currently blocking this mission.')+'</p>',engineering:'<p>'+esc((mission.suggested_files||[]).join(', ')||'Engineering files have not been identified yet.')+'</p>',pr:'<p class="muted">Pull request information appears after PR creation.</p>',deployment:'<p class="muted">Deployment status appears after deployment preview or execution.</p>',verification:'<p class="muted">Verification results appear after health checks run.</p>',rollback:'<p class="muted">Rollback guidance appears only if production verification fails.</p>',discussion:'<p class="muted">Discussion remains available in the Board Room.</p>'};
  return '<div class="mission-workspace"><div class="actions">'+tabs.map(function(t,i){return '<button class="secondary mission-workspace-tab" data-tab="'+t[0]+'">'+esc(t[1])+'</button>'}).join('')+'</div>'+tabs.map(function(t,i){return '<div class="mission-workspace-pane" data-pane="'+t[0]+'" style="'+(i?'display:none':'')+'"><h3>'+esc(t[1])+'</h3>'+content[t[0]]+'</div>'}).join('')+'</div>';
}
function presentMission(response){
  var mission=missionFrom(response), health=mission.health||{}, confidence=mission.mission_confidence||{}, business=mission.business_value||{};
  var progress=mission.progress_percentage===null?null:(typeof mission.progress_percentage==='number'?mission.progress_percentage:undefined);
  return {title:inferMissionTitle(response),mission_id:mission.mission_id||'Unknown',status:translateStage(mission.current_stage||mission.current_autonomous_stage||mission.status),executive_summary:executiveSummary(response),next_action:nextAction(response),progress_percentage:progress,health_label:health.label||'Not assessed',health_meaning:health.meaning||'No health issue reported.',confidence_score:confidence.score||'Not scored',confidence_reason:confidence.reason||'Not assessed',business_value:business.description||mission.objective||'Business value not assessed yet.'};
}
function missionCardHtml(response,raw){
  var p=presentMission(response);
  var mission=missionFrom(response);
  return '<h2>Mission: '+esc(p.title)+'</h2><div class="row"><span>Mission ID</span><span>'+esc(p.mission_id)+'</span></div><div class="row"><span>Workflow Run ID</span><span>'+esc(mission.workflow_run_id||'Not linked')+'</span></div><div class="row"><span>Status</span><span class="tag">'+esc(p.status)+'</span></div><div class="row"><span>Progress</span><span>'+esc(progressLabel(p.progress_percentage))+'</span></div><h3>Executive Summary</h3><p>'+esc(p.executive_summary)+'</p><h3>Mission Snapshot</h3><div class="row"><span>Business value</span><span>'+esc(p.business_value)+'</span></div><div class="row"><span>Health</span><span>'+esc(p.health_label+' - '+p.health_meaning)+'</span></div><div class="row"><span>Confidence</span><span>'+esc(p.confidence_score+' - '+p.confidence_reason)+'</span></div><h3>Progress</h3>'+progressHtml(response)+workspaceTabsHtml(response)+governanceHtml(response)+'<h3>Recommended Next Action</h3><p class="good">'+esc(p.next_action)+'</p>'+actionButtonsHtml(response)+detailsHtml(raw||response,'View Technical Details');
}
function missionCreatedHtml(response){
  var mission=missionFrom(response), p=presentMission(response), stage=mission.current_stage||mission.current_autonomous_stage||mission.status||'unknown';
  return '<h2>Mission Created Successfully</h2><div class="row"><span>Mission</span><span>'+esc(p.title)+'</span></div><div class="row"><span>ID</span><span>'+esc(p.mission_id)+'</span></div><div class="row"><span>Status</span><span class="tag">'+esc(p.status)+'</span></div><div class="row"><span>Stage</span><span>'+esc(humanize(stage))+'</span></div><div class="row"><span>Approval required</span><span>'+esc(mission.approval_required?'Yes':'No')+'</span></div><h3>Progress</h3>'+progressHtml(response)+'<h3>Next Action</h3><p class="good">'+esc(p.next_action)+'</p>'+detailsHtml(response,'View Technical Details');
}
document.addEventListener('click',function(e){var t=e.target;if(t&&t.classList&&t.classList.contains('mission-workspace-tab')){var root=t.closest('.mission-workspace');if(root){root.querySelectorAll('.mission-workspace-pane').forEach(function(p){p.style.display=p.dataset.pane===t.dataset.tab?'block':'none'})}}if(t&&t.classList&&t.classList.contains('mission-workspace-jump')&&window.showSection){window.showSection(t.dataset.target)}});
window.ExecutivePresenter={translateStage:translateStage,inferMissionTitle:inferMissionTitle,presentMission:presentMission,missionCardHtml:missionCardHtml,missionCreatedHtml:missionCreatedHtml,progressHtml:progressHtml,recommendationHtml:recommendationHtml,technicalDetailsHtml:detailsHtml,json:json,escape:esc};
})();</script>"""
