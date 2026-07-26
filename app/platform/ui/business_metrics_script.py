from __future__ import annotations


def render_business_metrics_script() -> str:
    return r"""<script>(function(){
function byId(id){return document.getElementById(id)}
function setTile(id,claim,formatter){
  var el=byId(id);if(!el)return;
  if(!claim||claim.status==='unknown'||claim.value===null||claim.value===undefined){el.textContent='Unknown';el.title=claim&&claim.unknown_reason?claim.unknown_reason:'No current evidence is available.';return}
  el.textContent=formatter?formatter(claim.value):String(claim.value);
  el.title='Source: '+(claim.source||'unknown')+'; checked: '+(claim.checked_at||'unknown');
}
window.refreshBusinessMetrics=async function(){
  try{
    var response=await fetch('/mission-control/business-metrics');
    if(!response.ok)throw new Error('HTTP '+response.status);
    var data=await response.json();
    setTile('kpiCustomers',data.customers);
    setTile('kpiSignups30d',data.signups_last_30d);
    setTile('kpiTeamMembers',data.team_members);
    setTile('kpiMrr',data.mrr_cents,function(cents){return '$'+(cents/100).toFixed(2)});
  }catch(error){
    ['kpiCustomers','kpiSignups30d','kpiTeamMembers','kpiMrr'].forEach(function(id){var el=byId(id);if(el)el.textContent='Unknown'});
  }
}
})();</script>"""
