from __future__ import annotations


LINEAGE_SECTION = """<section id="lineage" class="section">
<div class="card hero"><h2>Autonomous Delivery Lineage</h2><p class="muted">Evidence-backed mission replay from founder request through governed production acceptance.</p>
<div class="actions"><input id="lineageMissionId" placeholder="Mission ID (optional)" style="max-width:300px"><input id="lineageWorkflowId" placeholder="Workflow Run ID (optional)" style="max-width:340px"><button class="primary" id="lineageLoad">Load Lineage</button></div><p id="lineageSummary" class="muted">Load the latest durable mission or enter an identity.</p></div>
<div class="card"><div class="actions"><select id="lineageMode" style="max-width:190px"><option value="chronological">Chronological replay</option><option value="causal">Causal replay</option></select><input id="lineageStage" placeholder="Filter stage" style="max-width:220px"><label><input id="lineageFailures" type="checkbox" style="width:auto"> Failures and repair</label><label><input id="lineageGovernance" type="checkbox" style="width:auto"> Governance</label><label><input id="lineageDeployment" type="checkbox" style="width:auto"> Repository and deployment</label></div></div>
<div class="layout"><div class="card"><h2>Mission Journey</h2><div id="lineageEntries"><p class="muted">No lineage loaded.</p></div></div><div><div class="card"><h2>Current Boundary</h2><div id="lineageBoundary"><p class="muted">No governance evidence loaded.</p></div></div><div class="card"><h2>Evidence Quality</h2><div id="lineageGaps"><p class="muted">Unknown until lineage is loaded.</p></div></div></div></div>
<style>.lineage-entry{border-left:3px solid #3b82f6;padding:10px 12px;margin:0 0 10px;background:#0b1729;border-radius:0 8px 8px 0}.lineage-entry.failed{border-color:#ef4444}.lineage-entry small{display:block;color:var(--muted);margin-top:5px}.lineage-entry button{margin-top:7px}</style>
</section>"""


def render_delivery_lineage_script() -> str:
    return """<script>
(function(){
  function id(v){return document.getElementById(v)}
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function token(){return localStorage.getItem('mission_control_token')||''}
  async function post(body){var response=await fetch('/mission-control/delivery-lineage/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});var data=await response.json();if(!response.ok||data.status==='unauthorized')throw new Error(data.error||'Delivery lineage is unavailable.');return data}
  function payload(){return {token:token(),mission_id:id('lineageMissionId').value.trim(),workflow_run_id:id('lineageWorkflowId').value.trim(),mode:id('lineageMode').value,stage:id('lineageStage').value.trim(),failures_only:id('lineageFailures').checked,governance_only:id('lineageGovernance').checked,deployment_only:id('lineageDeployment').checked}}
  function entryCard(item){
    var refs=[].concat(item.artifact_refs||[],item.repository_refs||[],item.deployment_refs||[],item.evidence_refs||[]);
    return '<article class="lineage-entry '+(item.status==='failed'||item.status==='blocked'?'failed':'')+'"><strong>'+esc(item.sequence)+'. '+esc(item.summary)+'</strong><small>'+esc(item.stage)+' · '+esc(item.status)+' · '+esc(item.authority)+'</small><small>'+esc(item.occurred_at||'Time unknown')+' · '+esc(item.actor_id||'System')+'</small><details><summary>Evidence and provenance</summary><div class="row"><span>Provider</span><strong>'+esc(item.provider||'Unknown')+' · '+esc(item.model||'Unknown')+'</strong></div><div class="row"><span>Causality</span><strong>'+esc(item.causality||'unknown')+'</strong></div><p class="muted">'+esc(refs.join(' · ')||'No additional evidence reference recorded.')+'</p></details></article>';
  }
  function render(data){
    window.deliveryLineage=data;
    id('lineageMissionId').value=data.mission.mission_id||'';
    id('lineageWorkflowId').value=data.workflow_run.workflow_run_id||'';
    id('lineageSummary').textContent=data.filtered_entry_count+' of '+data.entry_count+' entries · '+data.current_stage+' · '+data.provider_model.provider+' '+data.provider_model.model;
    id('lineageEntries').innerHTML=data.entries.map(entryCard).join('')||'<p class="muted">No entries match these filters.</p>';
    var boundary=data.governance_state.current_boundary;
    id('lineageBoundary').innerHTML='<div class="row"><span>Status</span><strong>'+esc(data.current_status)+'</strong></div><div class="row"><span>Approval records</span><strong>'+esc(data.governance_state.approval_count)+'</strong></div><p>'+esc(typeof boundary==='string'?boundary:JSON.stringify(boundary||'No active boundary'))+'</p><p><strong>Next:</strong> '+esc(typeof data.next_action==='string'?data.next_action:JSON.stringify(data.next_action||'Inspect evidence'))+'</p>';
    id('lineageGaps').innerHTML='<div class="row"><span>Completeness</span><strong>'+esc(data.gaps.classification)+'</strong></div><div class="row"><span>Known gaps</span><strong>'+esc(data.gaps.gap_count)+'</strong></div>'+(data.gaps.items||[]).map(function(g){return '<p><strong>'+esc(g.code)+'</strong><br><span class="muted">'+esc(g.detail)+'</span></p>'}).join('');
  }
  async function load(){id('lineageSummary').textContent='Reconstructing durable delivery evidence...';try{var data=await post(payload());if(data.status==='mission-not-found')throw new Error('No matching durable mission was found.');render(data)}catch(error){id('lineageSummary').textContent=error.message||String(error)}}
  if(id('lineageLoad'))id('lineageLoad').addEventListener('click',load);
  ['lineageMode','lineageFailures','lineageGovernance','lineageDeployment'].forEach(function(key){if(id(key))id(key).addEventListener('change',function(){if(window.deliveryLineage)load()})});
  window.loadDeliveryLineage=load;
})();
</script>"""
