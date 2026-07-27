from __future__ import annotations


MEMORY_SECTION = """<section id="memory" class="section memory-shell" aria-labelledby="memoryTitle">
<div class="card hero"><p class="eyebrow">Cognitive Memory</p><h2 id="memoryTitle">Grounded facts, recall, and self-corrected answers</h2><p class="muted">Entities and edges are exact-match verified facts. Episodes are recall/context, never treated as verified on their own. Every answer below is checked against verified facts and self-corrected if it contradicts them.</p></div>
<div class="grid" id="memoryMetrics"><div class="card"><div class="small">Entities</div><div class="kpi" id="memEntityCount">Loading…</div></div><div class="card"><div class="small">Verified facts</div><div class="kpi" id="memFactCount">Loading…</div></div><div class="card"><div class="small">Episodes</div><div class="kpi" id="memEpisodeCount">Loading…</div></div></div>
<div class="card">
  <h2>Ask (grounded + self-correcting)</h2>
  <p class="muted">Answers are generated using only verified facts. If the model's own restatement of its answer contradicts a verified fact, it is automatically asked to revise before you see it.</p>
  <textarea id="memAskQuestion" placeholder="Example: Who founded AI Software Factory?"></textarea>
  <div class="actions"><button class="primary" id="memAskBtn">Ask</button></div>
  <div id="memAskResult" class="notice">No question asked yet.</div>
</div>
<div class="card">
  <h2>Save a fact</h2>
  <p class="muted">Free text is parsed into entities and edges. Only facts explicitly stated in the text are extracted - nothing is inferred. Prefer letting the platform record structured events automatically where possible; this is for facts that only exist as prose (founder notes, decisions).</p>
  <textarea id="memSaveText" placeholder="Example: The architect_agent reports to the cto_agent."></textarea>
  <div class="actions"><button class="primary" id="memSaveBtn">Save fact</button></div>
  <div id="memSaveResult" class="notice">No fact saved yet.</div>
</div>
<div class="layout">
  <div class="card">
    <h2>Verified facts</h2>
    <div class="actions"><input id="memFactFilter" placeholder="Filter by entity name"><button class="secondary" id="memFactSearchBtn">Search</button></div>
    <div id="memFactList" class="mem-list"><p class="muted">Load facts to inspect the knowledge graph.</p></div>
  </div>
  <div class="card">
    <h2>Recent episodes</h2>
    <div class="actions"><input id="memEpisodeQuery" placeholder="Search episodes"><button class="secondary" id="memEpisodeSearchBtn">Search</button></div>
    <div id="memEpisodeList" class="mem-list"><p class="muted">No episodes loaded.</p></div>
  </div>
</div>
<style>.memory-shell textarea{width:100%;min-height:90px;border:1px solid var(--line);background:#07101e;color:var(--text);border-radius:10px;padding:10px;font:inherit}.memory-shell input{border:1px solid var(--line);background:#07101e;color:var(--text);border-radius:10px;padding:10px;font:inherit}.mem-list{display:grid;gap:8px;max-height:420px;overflow:auto}.mem-fact,.mem-episode{border:1px solid var(--line);border-radius:8px;padding:10px;background:#07101e}.mem-fact strong{color:#93c5fd}.mem-episode small{color:var(--muted)}.mem-contradiction{border-color:#7f1d1d;background:#1a0d0d}</style>
</section>"""


def render_cognitive_memory_script() -> str:
    return """<script>
(function(){
'use strict';
function byId(id){return document.getElementById(id)}
function token(){return localStorage.getItem('mission_control_token')||''}
function esc(value){var node=document.createElement('span');node.textContent=String(value==null?'':value);return node.innerHTML}
async function request(path,payload){var response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({token:token()},payload||{}))});var data=await response.json().catch(function(){return {status:'error',error:'The service returned an unreadable response.'}});if(!response.ok||data.status==='unauthorised')throw new Error(data.error||'Cognitive memory data is unavailable.');return data}
function factRow(fact){return '<div class="mem-fact"><strong>'+esc(fact.source.name||fact.source.entity_id)+'</strong> —['+esc(fact.relationship)+']→ <strong>'+esc(fact.target.name||fact.target.entity_id)+'</strong><br><small class="muted">'+esc(fact.confidence)+'</small></div>'}
function episodeRow(item){return '<div class="mem-episode"><div>'+esc(item.content)+'</div><small>'+esc(item.source_type)+' · '+esc(item.created_at)+(item.similarity!=null?' · similarity '+esc(item.similarity):'')+'</small></div>'}
async function loadOverview(){
  try{
    var data=await request('/mission-control/cognitive-memory/overview',{});
    byId('memEntityCount').textContent=data.metrics.entity_count;
    byId('memFactCount').textContent=data.metrics.fact_count;
    byId('memEpisodeCount').textContent=data.metrics.episode_count;
    byId('memEpisodeList').innerHTML=(data.recent_episodes||[]).map(episodeRow).join('')||'<p class="muted">No episodes recorded yet.</p>';
  }catch(error){byId('memEntityCount').textContent='Unknown';byId('memFactCount').textContent='Unknown';byId('memEpisodeCount').textContent='Unknown'}
}
async function loadFacts(){
  var result=byId('memFactList');result.innerHTML='<p class="muted">Loading…</p>';
  try{
    var data=await request('/mission-control/cognitive-memory/facts',{entity_name:byId('memFactFilter').value});
    result.innerHTML=(data.facts||[]).map(factRow).join('')||'<p class="muted">No verified facts match this filter.</p>';
  }catch(error){result.innerHTML='<div class="notice error">'+esc(error.message)+'</div>'}
}
async function searchEpisodes(){
  var result=byId('memEpisodeList');var queryText=byId('memEpisodeQuery').value;
  if(!queryText){loadOverview();return}
  result.innerHTML='<p class="muted">Searching…</p>';
  try{
    var data=await request('/mission-control/cognitive-memory/episodes/search',{query_text:queryText,limit:10});
    result.innerHTML=(data.episodes||[]).map(episodeRow).join('')||'<p class="muted">No episodes match this search.</p>';
  }catch(error){result.innerHTML='<div class="notice error">'+esc(error.message)+'</div>'}
}
async function askQuestion(){
  var result=byId('memAskResult');var question=byId('memAskQuestion').value.trim();
  if(!question){result.className='notice error';result.textContent='Enter a question first.';return}
  result.className='notice';result.textContent='Retrieving facts and generating a grounded answer…';
  try{
    var data=await request('/mission-control/cognitive-memory/ask',{question:question});
    if(data.status!=='answered'){result.className='notice error';result.textContent=data.error||('Could not answer (status: '+data.status+').');return}
    var correctionNote=data.self_corrected?'<p><strong>Self-corrected</strong> after '+esc(data.correction_attempts)+' attempt(s) - the initial answer contradicted a verified fact and was revised.</p>':'';
    var unresolved=(data.unresolved_contradictions||[]).length?'<div class="mem-contradiction" style="padding:10px;border-radius:8px;margin-top:8px"><strong>Unresolved contradictions</strong><br>'+data.unresolved_contradictions.map(function(c){return esc(c.claim.subject+' -['+c.claim.predicate+']-> '+c.claim.object+' (verified: '+c.verified_object+')')}).join('<br>')+'</div>':'';
    result.innerHTML='<p>'+esc(data.answer)+'</p>'+correctionNote+unresolved+'<p class="muted">Grounded on '+esc((data.facts_used||[]).length)+' verified fact(s).</p>';
    loadOverview();
  }catch(error){result.className='notice error';result.textContent=error.message}
}
async function saveFact(){
  var result=byId('memSaveResult');var text=byId('memSaveText').value.trim();
  if(!text){result.className='notice error';result.textContent='Enter some text first.';return}
  result.className='notice';result.textContent='Extracting facts…';
  try{
    var data=await request('/mission-control/cognitive-memory/save-fact',{text:text});
    if(data.status==='no_facts_found'){result.className='notice';result.textContent='No explicit facts were found in that text.';return}
    if(data.status!=='saved'){result.className='notice error';result.textContent=data.error||('Could not save (status: '+data.status+').');return}
    result.innerHTML='Saved '+esc(data.entities.length)+' entit'+(data.entities.length===1?'y':'ies')+' and '+esc(data.edges.length)+' edge(s). Embedding: '+esc(data.embedding_status)+'.';
    byId('memSaveText').value='';
    loadOverview();loadFacts();
  }catch(error){result.className='notice error';result.textContent=error.message}
}
document.addEventListener('DOMContentLoaded',function(){
  byId('memAskBtn').onclick=askQuestion;
  byId('memSaveBtn').onclick=saveFact;
  byId('memFactSearchBtn').onclick=loadFacts;
  byId('memEpisodeSearchBtn').onclick=searchEpisodes;
  var nav=document.querySelector('[data-section="memory"]');if(nav)nav.addEventListener('click',function(){loadOverview();loadFacts()});
  if(window.location.hash==='#memory'){loadOverview();loadFacts()}
});
})();
</script>"""
