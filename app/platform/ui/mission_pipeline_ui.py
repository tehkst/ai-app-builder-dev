from __future__ import annotations


def render_mission_pipeline_script() -> str:
    return r"""<script>(function(){
var activeMissionId=null;
function byId(id){return document.getElementById(id)}
function render(data){return typeof data==='string'?data:JSON.stringify(data,null,2)}
function safe(value){return String(value||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function showSection(name){if(window.showSection){window.showSection(name);return}var btn=document.querySelector('.nav button[data-section="'+name+'"]');if(btn)btn.click()}
function installMissionPipelinePanel(){
  var section=byId('execution');if(!section||byId('missionPipelineDashboard'))return;
  var panel=document.createElement('div');
  panel.innerHTML='<div class="card hero"><h2>Executive Mission View</h2><p class="muted">CEO-level mission health, progress, confidence, owner, ETA, and next decision. All fields are derived from existing Mission Control systems.</p><div class="actions"><button class="secondary" id="pipelineRefreshBtn">Refresh Missions</button><button class="secondary" id="pipelineOpenBoardBtn">Open Board Room</button><button class="secondary" id="pipelineOpenComponentsBtn">Open Component Panels</button></div><pre id="missionPipelineResult" style="display:none">No pipeline result yet.</pre></div><div class="grid"><div class="card"><h2>Missions</h2><div id="missionPipelineDashboard">No missions loaded.</div><p id="missionPipelineSummary" class="muted"></p></div><div class="card"><h2>Mission Detail</h2><div id="missionPipelineDetail">Select a mission to inspect executive summary, health, recommendation, blocker, and timeline.</div></div></div>';
  section.insertBefore(panel,section.firstChild);
  byId('pipelineRefreshBtn').addEventListener('click',refreshMissionPipeline);
  byId('pipelineOpenBoardBtn').addEventListener('click',function(){showSection('board')});
  byId('pipelineOpenComponentsBtn').addEventListener('click',function(){showSection('executions')});
}
async function fetchJson(url){return fetch(url).then(function(r){return r.json()})}
async function refreshMissionPipeline(){
  try{var data=await fetchJson('/mission-control/pipeline');renderDashboard(data);byId('missionPipelineResult').textContent=render(data)}
  catch(e){byId('missionPipelineResult').textContent='Mission pipeline refresh failed: '+e}
}
async function openPipelineMission(id){
  activeMissionId=id;
  try{var data=await fetchJson('/mission-control/pipeline/'+encodeURIComponent(id));renderDetail(data.mission);byId('missionPipelineResult').textContent=render(data)}
  catch(e){byId('missionPipelineResult').textContent='Mission detail failed: '+e}
}
async function refreshRecommendation(){
  if(!activeMissionId)return;
  try{var data=await fetchJson('/mission-control/pipeline/'+encodeURIComponent(activeMissionId)+'/recommendation');var box=byId('pipelineRecommendationBox');if(box)box.textContent=render(data.recommendation)}
  catch(e){var box=byId('pipelineRecommendationBox');if(box)box.textContent='Recommendation failed: '+e}
}
async function refreshTimeline(){
  if(!activeMissionId)return;
  try{var data=await fetchJson('/mission-control/pipeline/'+encodeURIComponent(activeMissionId)+'/timeline');var box=byId('pipelineTimelineBox');if(box)box.innerHTML=timelineHtml(data.timeline||[])}
  catch(e){var box=byId('pipelineTimelineBox');if(box)box.textContent='Timeline failed: '+e}
}
function renderDashboard(data){
  var box=byId('missionPipelineDashboard');if(!box)return;
  var missions=(data&&data.missions)||[];
  var summary=data&&data.summary||{};
  byId('missionPipelineSummary').textContent='Summary: '+(summary.active||0)+' Active | '+(summary.blocked||0)+' Blocked | '+(summary.complete||0)+' Complete';
  if(!missions.length){box.innerHTML='<p class="muted">No missions observed yet. Create missions through existing Board Room or Execution tools.</p>';return}
  box.innerHTML=missions.map(function(m){var h=m.health||{};var bv=m.business_value||{};var mc=m.mission_confidence||{};return '<button class="secondary pipeline-open" data-id="'+safe(m.mission_id)+'" style="width:100%;text-align:left;margin:7px 0"><strong>'+safe(m.mission_label)+'</strong><br><span>Health: '+safe(h.icon||'')+' '+safe(h.label||'Unknown')+' · Progress: '+safe(m.progress_percentage)+'%</span><br><span>Status: '+safe(m.status)+' · Owner: '+safe(m.current_owner||'Unknown')+'</span><br><span>Confidence: '+safe(mc.score)+'% · ETA: '+safe(m.eta||'Not computable')+'</span><br><span>Business Impact: '+safe(bv.description||'Not assessed')+'</span><br><span>Next Action: '+safe(m.next_action)+'</span><br><span class="small">Blocking: '+safe(m.blocking_reason||'None')+'</span></button>'}).join('');
  box.querySelectorAll('.pipeline-open').forEach(function(btn){btn.addEventListener('click',function(){openPipelineMission(this.dataset.id)})});
}
function renderDetail(mission){
  var box=byId('missionPipelineDetail');if(!box)return;if(!mission){box.innerHTML='<p class="muted">Mission not found.</p>';return}
  activeMissionId=mission.mission_id;
  var h=mission.health||{}, bv=mission.business_value||{}, mc=mission.mission_confidence||{};
  box.innerHTML='<h3>'+safe(mission.mission_label)+'</h3><h3>Executive Summary</h3><p>'+safe(mission.executive_summary)+'</p><div class="row"><span>Mission Objective</span><span>'+safe(mission.objective)+'</span></div><div class="row"><span>Business Value</span><span>'+safe(bv.impact)+' impact · '+safe(bv.risk)+' risk · '+safe(bv.description)+'</span></div><div class="row"><span>Health</span><span class="'+(h.label==='Blocked'||h.label==='Failed'?'warn':'good')+'">'+safe(h.icon)+' '+safe(h.label)+' - '+safe(h.meaning)+'</span></div><div class="row"><span>Progress</span><span>'+safe(mission.progress_percentage)+'%</span></div><div class="row"><span>Current Owner</span><span>'+safe(mission.current_owner)+'</span></div><div class="row"><span>ETA</span><span>'+safe(mission.eta)+'</span></div><div class="row"><span>Overall Confidence</span><span>'+safe(mc.score)+'% - '+safe(mc.reason)+'</span></div><div class="row"><span>Status</span><span class="tag">'+safe(mission.status)+'</span></div><div class="row"><span>Next Action</span><span class="good">'+safe(mission.next_action)+'</span></div><div class="row"><span>Blocking</span><span class="'+(mission.blocking_reason&&mission.blocking_reason!=='None'?'warn':'good')+'">'+safe(mission.blocking_reason||'None')+'</span></div><div class="actions"><button class="secondary" id="pipelineRefreshRecommendationBtn">Refresh Recommendation</button><button class="secondary" id="pipelineRefreshTimelineBtn">Refresh Timeline</button><button class="primary" id="pipelineDelegateBtn">Open Existing Action Panel</button></div><h3>Recommendation</h3><pre id="pipelineRecommendationBox" style="min-height:80px">'+safe(render(mission.recommendation||{}))+'</pre><h3>Success Criteria</h3><ul>'+((mission.success_criteria||[]).map(function(item){return '<li>'+safe(item)+'</li>'}).join('')||'<li>Not available.</li>')+'</ul><h3>Mission Story</h3><div id="pipelineTimelineBox">'+timelineHtml(mission.timeline||[])+'</div><h3>Observed Source Snapshot</h3><pre style="min-height:120px">'+safe(render(mission.source_snapshot||{}))+'</pre>';
  byId('pipelineRefreshRecommendationBtn').addEventListener('click',refreshRecommendation);
  byId('pipelineRefreshTimelineBtn').addEventListener('click',refreshTimeline);
  byId('pipelineDelegateBtn').addEventListener('click',function(){delegateAction(mission)});
}
function timelineHtml(events){if(!events.length)return '<p class="muted">No timeline events observed.</p>';return '<ol>'+events.map(function(e){return '<li><strong>'+safe(e.timestamp)+'</strong> · '+safe(e.actor)+': '+safe(e.detail)+'</li>'}).join('')+'</ol>'}
function delegateAction(mission){
  var text=(mission.next_action||'').toLowerCase();
  if(text.indexOf('deployment')>=0||text.indexOf('deploy')>=0||text.indexOf('verification')>=0||text.indexOf('rollback')>=0||text.indexOf('github')>=0||text.indexOf('pr')>=0){showSection('executions');return}
  showSection('board');
}
window.openPipelineMission=openPipelineMission;window.refreshMissionPipeline=refreshMissionPipeline;
document.addEventListener('DOMContentLoaded',function(){installMissionPipelinePanel();refreshMissionPipeline()});
})();</script>"""
