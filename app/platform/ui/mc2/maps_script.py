"""Mission Control Maps: every codebase's Codebase Map in one place (app/platform/codebase_map).

Data: POST /mission-control/clients/maps (founder-only). Each codebase gets Open the map (the viewer,
new tab) and Make / Update / Redraw, behind the same confirmation as the Clients screen: the code is
sent to the AI provider named in the dialog, with that provider's terms. The screen polls while a
map is being drawn. Code is added under Clients. Every server string goes through esc().
"""
from __future__ import annotations

MAPS_SCRIPT = r"""
(function(){
  var MC=window.MC;var esc=MC.esc;var $=function(id){return document.getElementById(id)};
  var state={rows:[],provider:'',terms:null,timer:null};
  function tag(label,tone){return '<span class="mc-tag '+tone+'">'+esc(label)+'</span>'}
  function termsText(){var t=state.terms;if(!t)return '';
    return '\n\nWhat '+t.company+'\'s terms say (read '+(t.checked||'never')+'):\n- '+t.facts.join('\n- ')}
  function rowHtml(r){
    var m=r.map,st=m&&m.stats||{},name=r.client+' · '+r.label,html='<li class="mc-card mc-codebase"><div class="mc-person-head"><h3>'+esc(name)+'</h3>';
    if(m&&m.status==='running')html+=tag('Drawing the map…','run');else if(m&&m.status==='ready')html+=tag('Map ready','done');
    else if(m&&m.status==='failed')html+=tag('Problem','stuck');else html+=tag('No map yet','plain');
    html+='</div><p class="mc-empty">'+esc(r.source)+'</p>';
    if(m&&m.status==='running')html+='<p class="mc-empty">The Codebase Cartographer is reading the code. Big codebases take a while.</p>';
    if(m&&m.status==='failed')html+='<p class="mc-status bad">'+esc(m.error)+'</p>';
    if(m&&m.status==='ready'){
      html+='<p>'+esc(st.files)+' files · '+esc(st.routes)+' endpoints · '+esc(st.http_links)+' web requests traced · made '+esc(String(m.finished_at||'').slice(0,10))+
        (MC.costText(m.cost)?' <span class="mc-empty">· AI '+esc(MC.costText(m.cost))+'</span>':'')+'</p>'+
        ((m.health||[]).length?'<p>'+m.health.map(function(h){return tag(h.count+' · '+h.title,h.severity==='high'?'stuck':h.severity==='medium'?'needs':'plain')}).join(' ')+'</p>':'')}
    html+='<div class="mc-actions">';
    if(m&&m.status==='ready')html+='<a class="mc-btn" href="/mission-control/clients/map?id='+encodeURIComponent(m.map_id)+'" target="_blank" rel="noopener">Open the map</a>';
    if(r.can_map&&!(m&&m.status==='running')){var has=m&&m.status==='ready';
      html+='<button type="button" class="mc-btn'+(has?' secondary':'')+'" data-mapit="'+esc(r.codebase_id)+'">'+(has?'Update the map':'Make a map')+'</button>'+
        (has?'<button type="button" class="mc-btn secondary" data-mapit="'+esc(r.codebase_id)+'" data-redraw="1">Redraw from scratch</button>':'')}
    else if(!r.can_map)html+='<span class="mc-empty">The code isn\'t fetched yet (see Clients).</span>';
    return html+'</div></li>'}
  function render(){
    var box=$('mcMapList');
    box.innerHTML=state.rows.length?state.rows.map(rowHtml).join(''):
      '<li><p class="mc-empty">No code to map yet. Add a client and their code under Clients, then come back here.</p></li>';
    clearTimeout(state.timer);
    if(state.rows.some(function(r){return r.map&&r.map.status==='running'}))state.timer=setTimeout(load,5000)}
  async function load(){
    try{var d=await MC.post('/mission-control/clients/maps',{});if(d.error)throw new Error(d.error);
      state.rows=d.codebases;state.provider=d.ai_provider;state.terms=d.ai_terms;render()}
    catch(e){$('mcMapList').innerHTML='<li><p class="mc-status bad">'+esc(e.message)+'</p></li>'}}
  MC.onShow=MC.onShow||{};MC.onShow.maps=load;
  $('mcMapList').addEventListener('click',async function(e){
    var b=e.target.closest('[data-mapit]');if(!b)return;
    var r=state.rows.filter(function(x){return x.codebase_id===b.dataset.mapit})[0],redraw=b.dataset.redraw==='1';
    if(!state.provider){window.alert('Choose an AI provider in Settings first.');return}
    if(!window.confirm('The Codebase Cartographer will read "'+r.label+'" for '+r.client+' and draw '+(redraw?'a new map from scratch':r.map&&r.map.status==='ready'?'an updated map (only new and changed files are read again)':'its map')+'. Nothing is changed or run outside the sandbox.\n\n'+
      'To do this, the code is sent to '+state.provider+'. Only continue if '+r.client+' agreed to that.'+termsText()))return;
    b.disabled=true;
    var res=await MC.post('/mission-control/clients/run-map',{codebase_id:r.codebase_id,client_consent:true,ai_provider:state.provider,terms_version:state.terms&&state.terms.version,redraw:redraw});
    if(res.error)window.alert(res.error);load()});
})();
"""
