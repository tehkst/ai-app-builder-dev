from __future__ import annotations


# Node-link diagram: deterministic (no Math.random, so a reload doesn't jitter the
# layout) force-directed placement computed once per render, then drawn as static
# SVG - no continuous physics loop, so it never spins the CPU while idle.
_AKG_LAYOUT_JS = r"""
  var AKG_TYPE_COLOR={Module:'#38bdf8',Service:'#a78bfa',Artifact:'#fbbf24',Mission:'#34d399',Workflow:'#60a5fa',Agent:'#f472b6',Provider:'#fb923c',Technology:'#94a3b8',Runtime:'#22d3ee',Deployment:'#f87171'};
  var AKG_TYPE_RADIUS={Service:9,Runtime:9,Deployment:8,Mission:8,Provider:7,Technology:7,Agent:6,Workflow:6,Artifact:6,Module:5};
  var AKG_MAX_NODES=160;
  function akgHash(s){var h=0;for(var i=0;i<s.length;i++){h=(h*31+s.charCodeAt(i))|0}return Math.abs(h)}
  function akgColor(type){return AKG_TYPE_COLOR[type]||'#7dd3fc'}
  function akgRadius(type){return AKG_TYPE_RADIUS[type]||5}
  function akgLabel(node){var name=String(node.name||node.id||'');var short=name.split('.').slice(-1)[0];return short.length>22?short.slice(0,19)+'...':short}
  function akgLayout(nodes,edges,width,height){
    var types=[];nodes.forEach(function(n){if(types.indexOf(n.type)<0)types.push(n.type)});
    var byId={};nodes.forEach(function(n){byId[n.id]=n});
    var cx=width/2,cy=height/2,ring=Math.min(width,height)*0.38;
    var perType={};types.forEach(function(t,i){perType[t]={count:0,total:nodes.filter(function(n){return n.type===t}).length,angleBase:(i/types.length)*Math.PI*2}});
    var pos={};
    nodes.forEach(function(n){
      var group=perType[n.type];var slot=group.count++;
      var spread=group.total>1?(slot/group.total)*(Math.PI*1.6)-Math.PI*0.8:0;
      var angle=group.angleBase+spread;
      var jitter=(akgHash(n.id)%100)/100*0.25;
      var radius=ring*(0.55+jitter);
      pos[n.id]={x:cx+Math.cos(angle)*radius,y:cy+Math.sin(angle)*radius,vx:0,vy:0};
    });
    var restLength=Math.min(width,height)*0.16;
    var iterations=nodes.length>AKG_MAX_NODES?40:120;
    for(var it=0;it<iterations;it++){
      var cool=1-(it/iterations);
      nodes.forEach(function(a){
        var pa=pos[a.id],fx=0,fy=0;
        nodes.forEach(function(b){
          if(a.id===b.id)return;var pb=pos[b.id];var dx=pa.x-pb.x,dy=pa.y-pb.y;var d=Math.sqrt(dx*dx+dy*dy)||0.01;
          var repel=Math.min(2200/(d*d),40);fx+=(dx/d)*repel;fy+=(dy/d)*repel;
        });
        fx+=(cx-pa.x)*0.004;fy+=(cy-pa.y)*0.004;
        pa.vx=(pa.vx+fx)*0.35;pa.vy=(pa.vy+fy)*0.35;
      });
      edges.forEach(function(e){
        var pa=pos[e.source],pb=pos[e.target];if(!pa||!pb)return;
        var dx=pb.x-pa.x,dy=pb.y-pa.y;var d=Math.sqrt(dx*dx+dy*dy)||0.01;
        var pull=(d-restLength)*0.02;
        var ax=(dx/d)*pull,ay=(dy/d)*pull;
        pa.vx+=ax*cool;pa.vy+=ay*cool;pb.vx-=ax*cool;pb.vy-=ay*cool;
      });
      nodes.forEach(function(n){var p=pos[n.id];p.x+=p.vx*cool;p.y+=p.vy*cool});
    }
    var pad=26;
    nodes.forEach(function(n){var p=pos[n.id];p.x=Math.max(pad,Math.min(width-pad,p.x));p.y=Math.max(pad,Math.min(height-pad,p.y))});
    return pos;
  }
"""


# Rendering: builds one static <svg> (edges as <line>, nodes as a <g> wrapping a
# <circle>+<text> so both are one click target) plus the existing detail/impact
# panels and view/refresh controls, unchanged in contract from the prior version.
_AKG_RENDER_JS = r"""
  function svgEl(tag,attrs){var el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(var k in attrs){el.setAttribute(k,attrs[k])}return el}
  function akgBuildSvg(nodes,edges){
    var width=900,height=620;
    var shown=nodes.slice(0,AKG_MAX_NODES);
    var shownIds={};shown.forEach(function(n){shownIds[n.id]=true});
    var visibleEdges=edges.filter(function(e){return shownIds[e.source]&&shownIds[e.target]});
    var pos=akgLayout(shown,visibleEdges,width,height);
    var svg=svgEl('svg',{viewBox:'0 0 '+width+' '+height,width:'100%',height:'620',class:'akg-svg'});
    var edgeGroup=svgEl('g',{class:'akg-edges'});
    visibleEdges.forEach(function(e){
      var pa=pos[e.source],pb=pos[e.target];if(!pa||!pb)return;
      var line=svgEl('line',{x1:pa.x,y1:pa.y,x2:pb.x,y2:pb.y,class:'akg-edge'});
      var title=svgEl('title',{});title.textContent=e.type+' ('+(e.evidence||'evidence')+')';line.appendChild(title);
      edgeGroup.appendChild(line);
    });
    svg.appendChild(edgeGroup);
    var nodeGroup=svgEl('g',{class:'akg-nodes-g'});
    shown.forEach(function(n){
      var p=pos[n.id];if(!p)return;
      var g=svgEl('g',{class:'akg-node-g',tabindex:'0','data-akg-node':n.id,transform:'translate('+p.x+','+p.y+')'});
      g.appendChild(svgEl('circle',{r:akgRadius(n.type),class:'akg-dot',fill:akgColor(n.type)}));
      var text=svgEl('text',{x:akgRadius(n.type)+4,y:4,class:'akg-label'});text.textContent=akgLabel(n);
      g.appendChild(text);
      var title=svgEl('title',{});title.textContent=n.name+' ('+n.type+')';g.appendChild(title);
      nodeGroup.appendChild(g);
    });
    svg.appendChild(nodeGroup);
    return {svg:svg,truncated:nodes.length>AKG_MAX_NODES};
  }
  function id(value){return document.getElementById(value)}
  function esc(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function token(){return localStorage.getItem('mission_control_token')||''}
  async function post(url,body){var response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});var data=await response.json();if(!response.ok||data.status==='unauthorized')throw new Error(data.error||'Architecture evidence is unavailable.');return data}
  function akgLegend(nodes){var types=[];nodes.forEach(function(n){if(types.indexOf(n.type)<0)types.push(n.type)});return types.map(function(t){return '<span class="akg-legend-item"><i style="background:'+akgColor(t)+'"></i>'+esc(t)+'</span>'}).join('')}
  function renderGraph(data){
    window.akgCurrent=data;
    var built=akgBuildSvg(data.nodes,data.edges);
    id('akgSummary').textContent=data.nodes.length+' nodes · '+data.edges.length+' typed relationships · '+data.view+' view'+(built.truncated?' (showing first '+AKG_MAX_NODES+' nodes)':'');
    var container=id('akgNodes');
    container.innerHTML='<div class="akg-legend">'+akgLegend(data.nodes.slice(0,AKG_MAX_NODES))+'</div>';
    if(!data.nodes.length){container.innerHTML+='<p class="muted">No nodes match this projection.</p>'}else{container.appendChild(built.svg)}
    id('akgDetail').innerHTML='<p class="muted">Select a component to inspect evidence, dependencies, health, and architectural decisions.</p>';
  }
  function renderDetail(node){
    var quality=node.quality||{},operational=node.operational||{},decision=node.decision||{};
    var evidence=(node.evidence||[]).map(function(item){return '<li>'+esc(item.kind||'evidence')+': '+esc(item.source||'unknown')+'</li>'}).join('');
    id('akgDetail').innerHTML='<h3>'+esc(node.name)+'</h3><div class="row"><span>Type</span><strong>'+esc(node.type)+'</strong></div><div class="row"><span>Authority</span><strong>'+esc(node.authority||'Unknown')+'</strong></div><div class="row"><span>Lifecycle</span><strong>'+esc(node.lifecycle||'Unknown')+'</strong></div><div class="row"><span>Health</span><strong>'+esc((node.health||{}).status||'Unknown')+'</strong></div><div class="row"><span>LOC rule</span><strong>'+esc(quality.line_rule||'Not applicable')+'</strong></div><div class="row"><span>Runtime usage</span><strong>'+esc(operational.runtime_usage||'Unknown')+'</strong></div><h3>Why it exists</h3><p>'+esc(decision.why_introduced||node.purpose||'No explicit architectural rationale is currently recorded.')+'</p><h3>Decision</h3><p>'+esc(decision.decision||'Derived from current repository and authority evidence.')+'</p><h3>Evidence</h3><ul>'+evidence+'</ul>';
  }
  function renderImpact(data){
    id('akgImpactResult').innerHTML='<h3>Impact assessment</h3><div class="row"><span>Complexity</span><strong>'+esc(data.estimated_complexity)+'</strong></div><div class="row"><span>Affected modules</span><strong>'+esc(data.affected_modules.length)+'</strong></div><div class="row"><span>Affected tests</span><strong>'+esc(data.affected_tests.length)+'</strong></div><div class="row"><span>Deployments</span><strong>'+esc(data.affected_deployments.join(', ')||'None proven')+'</strong></div><p><strong>Migration order</strong></p><ol>'+data.migration_order.slice(0,30).map(function(item){return '<li>'+esc(item)+'</li>'}).join('')+'</ol>';
  }
  async function loadGraph(refresh){
    id('akgSummary').textContent='Projecting live architecture evidence...';
    try{renderGraph(await post('/mission-control/architecture-knowledge-graph/project',{token:token(),view:id('akgView').value,refresh:!!refresh}))}catch(error){id('akgSummary').textContent=error.message||String(error)}
  }
  async function analyzeImpact(){
    var target=id('akgImpactTarget').value.trim();if(!target){id('akgImpactResult').textContent='Enter a technology, provider, module, or service.';return}
    id('akgImpactResult').textContent='Computing dependency blast radius...';
    try{renderImpact(await post('/mission-control/architecture-knowledge-graph/impact',{token:token(),target:target}))}catch(error){id('akgImpactResult').textContent=error.message||String(error)}
  }
  document.addEventListener('click',function(event){
    var nodeButton=event.target.closest&&event.target.closest('[data-akg-node]');
    if(nodeButton&&window.akgCurrent){
      document.querySelectorAll('.akg-node-g.selected').forEach(function(el){el.classList.remove('selected')});
      nodeButton.classList.add('selected');
      var node=window.akgCurrent.nodes.find(function(item){return item.id===nodeButton.dataset.akgNode});if(node)renderDetail(node)
    }
  });
  document.addEventListener('DOMContentLoaded',function(){
    if(id('akgLoad'))id('akgLoad').addEventListener('click',function(){loadGraph(false)});
    if(id('akgRefresh'))id('akgRefresh').addEventListener('click',function(){loadGraph(true)});
    if(id('akgImpact'))id('akgImpact').addEventListener('click',analyzeImpact);
    if(id('akgView'))id('akgView').addEventListener('change',function(){loadGraph(false)});
  });
  window.loadArchitectureKnowledgeGraph=loadGraph;
"""

_AKG_STYLE_JS = r"""
  (function(){
    var style=document.createElement('style');
    style.textContent='#akgNodes{display:block}.akg-svg{background:#050d19;border-radius:6px}.akg-edge{stroke:#25405e;stroke-width:1}.akg-node-g{cursor:pointer}.akg-node-g:hover .akg-dot,.akg-node-g.selected .akg-dot{stroke:#e2f2ff;stroke-width:2}.akg-node-g:focus-visible .akg-dot{outline:none;stroke:#38bdf8;stroke-width:2}.akg-label{fill:#b7c8de;font-size:9px;font-family:ui-sans-serif,system-ui,sans-serif}.akg-legend{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:8px;font-size:11px;color:var(--muted)}.akg-legend-item{display:flex;align-items:center;gap:5px}.akg-legend-item i{width:9px;height:9px;border-radius:50%;display:inline-block}';
    document.head.appendChild(style);
  })();
"""


def render_architecture_graph_script() -> str:
    return "<script>\n(function(){\n" + _AKG_LAYOUT_JS + _AKG_RENDER_JS + _AKG_STYLE_JS + "\n})();\n</script>"
