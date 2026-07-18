from __future__ import annotations


def render_executive_state_script() -> str:
    return r"""<script>(function(){
function byId(id){return document.getElementById(id)}
function htmlEscape(value){return String(value===null||value===undefined?'':value).replace(/[&<>\"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]})}
function claimText(claim){
  if(!claim||claim.status==='unknown'||claim.value===null||claim.value===undefined)return 'Unknown';
  if(Array.isArray(claim.value)){
    if(!claim.value.length)return 'None observed';
    return claim.value[0]&&claim.value[0].reason?claim.value[0].reason:(claim.value.length+' observed');
  }
  if(typeof claim.value==='object')return claim.value.title||claim.value.mission_id||claim.value.overall||claim.value.status||'Observed';
  return String(claim.value)
}
function claimReason(claim){return claim&&claim.unknown_reason?claim.unknown_reason:'No current evidence is available.'}
function executiveRow(label,claim){
  var unknown=!claim||claim.status==='unknown'||claim.value===null||claim.value===undefined;
  var detail=unknown?claimReason(claim):('Source: '+(claim.source||'unknown')+'; checked: '+(claim.checked_at||'unknown'));
  return '<div class="row"><span>'+htmlEscape(label)+'</span><span class="'+(unknown?'muted':'tag')+'" title="'+htmlEscape(detail)+'">'+htmlEscape(claimText(claim))+'</span></div>'
}
window.refreshExecutiveState=async function(){
  var home=byId('home'),projects=byId('projects');
  try{
    var response=await fetch('/mission-control/executive-intelligence/briefing');
    if(!response.ok)throw new Error('HTTP '+response.status);
    var data=await response.json(),mission=data.active_mission||{},next=data.next_recommended_action||{},blockers=data.blockers||{};
    var homeLayout=home&&home.querySelector('.layout');
    if(homeLayout)homeLayout.innerHTML='<div class="card"><h2>Live Executive State</h2>'+executiveRow('Repository',data.repository_identity)+executiveRow('Branch',data.branch)+executiveRow('HEAD',data.head_sha)+executiveRow('Active mission',mission)+executiveRow('Mission stage',data.mission_stage)+executiveRow('Project progress',data.project_progress)+'</div><div class="card"><h2>Current Evidence</h2>'+executiveRow('Platform health',data.platform_health)+executiveRow('Open pull requests',data.open_prs)+executiveRow('CI checks',data.ci_check_status)+executiveRow('Deployed revision',data.deployed_revision)+executiveRow('Production verification',data.production_verification)+executiveRow('Next action',next)+executiveRow('Blockers',blockers)+'</div>';
    if(projects)projects.innerHTML='<div class="card"><h2>Executive State</h2>'+executiveRow('Active mission',mission)+executiveRow('Current sprint',data.current_sprint)+executiveRow('Sprint progress',data.sprint_progress)+executiveRow('Release stage',data.release_stage)+executiveRow('Deployment traffic',data.deployment_traffic)+'</div>';
  }catch(error){
    var target=home&&home.querySelector('.layout');
    if(target)target.innerHTML='<div class="card"><h2>Live Executive State</h2><p class="muted">Executive evidence is currently unavailable: '+htmlEscape(error.message||error)+'</p></div>';
  }
}
})();</script>"""
