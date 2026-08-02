from __future__ import annotations

from app.platform.ui.architecture_graph_script.part_1 import _AKG_COMPLEXITY_JS, _AKG_LAYOUT_JS


# Rendering: builds one static <svg> (edges as <line>, nodes as a <g> wrapping a
# <circle>+<text> so both are one click target) plus the existing detail/impact
# panels and view/refresh controls, unchanged in contract from the prior version.
_AKG_RENDER_JS = r"""
  function svgEl(tag,attrs){var el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(var k in attrs){el.setAttribute(k,attrs[k])}return el}
  var akgView={tx:0,ty:0,scale:1};
  function akgApplyViewport(g){g.setAttribute('transform','translate('+akgView.tx+','+akgView.ty+') scale('+akgView.scale+')')}
  function akgWireViewport(svg,viewport,width,height){
    var dragging=false,lastX=0,lastY=0,moved=0;
    svg.style.cursor='grab';
    svg.addEventListener('mousedown',function(e){dragging=true;lastX=e.clientX;lastY=e.clientY;moved=0;svg.style.cursor='grabbing'});
    window.addEventListener('mousemove',function(e){
      if(!dragging)return;
      var dx=e.clientX-lastX,dy=e.clientY-lastY;
      moved+=Math.abs(dx)+Math.abs(dy);
      akgView.tx+=dx;akgView.ty+=dy;
      lastX=e.clientX;lastY=e.clientY;
      akgApplyViewport(viewport);
    });
    window.addEventListener('mouseup',function(){
      if(dragging&&moved>4)window.akgDidPan=true;
      dragging=false;svg.style.cursor='grab';
    });
    svg.addEventListener('wheel',function(e){
      e.preventDefault();
      var rect=svg.getBoundingClientRect();
      var mx=(e.clientX-rect.left)*(width/rect.width),my=(e.clientY-rect.top)*(height/rect.height);
      var factor=e.deltaY<0?1.15:1/1.15;
      var newScale=Math.max(0.2,Math.min(4,akgView.scale*factor));
      var ratio=newScale/akgView.scale;
      akgView.tx=mx-(mx-akgView.tx)*ratio;akgView.ty=my-(my-akgView.ty)*ratio;akgView.scale=newScale;
      akgApplyViewport(viewport);
    },{passive:false});
  }
  function akgBuildSvg(nodes,edges){
    var shown=nodes.slice(0,AKG_MAX_NODES);
    var shownIds={};shown.forEach(function(n){shownIds[n.id]=true});
    var visibleEdges=edges.filter(function(e){return shownIds[e.source]&&shownIds[e.target]});
    // World space scales with how many nodes are actually being laid out, instead
    // of a fixed 900x620 box that squeezed everything against its edges once
    // AKG_MAX_NODES got anywhere near its cap - see akgLayout's position clamp.
    var side=Math.max(900,Math.ceil(Math.sqrt(shown.length)*130));
    var width=side,height=Math.round(side*0.69);
    var pos=akgLayout(shown,visibleEdges,width,height);
    var svg=svgEl('svg',{viewBox:'0 0 '+width+' '+height,width:'100%',height:'620',class:'akg-svg'});
    akgView={tx:0,ty:0,scale:1};
    var viewport=svgEl('g',{class:'akg-viewport'});
    var edgeGroup=svgEl('g',{class:'akg-edges'});
    visibleEdges.forEach(function(e){
      var pa=pos[e.source],pb=pos[e.target];if(!pa||!pb)return;
      var line=svgEl('line',{x1:pa.x,y1:pa.y,x2:pb.x,y2:pb.y,class:'akg-edge'});
      var title=svgEl('title',{});title.textContent=e.type+' ('+(e.evidence||'evidence')+')';line.appendChild(title);
      edgeGroup.appendChild(line);
    });
    viewport.appendChild(edgeGroup);
    var nodeGroup=svgEl('g',{class:'akg-nodes-g'});
    shown.forEach(function(n){
      var p=pos[n.id];if(!p)return;
      var g=svgEl('g',{class:'akg-node-g',tabindex:'0','data-akg-node':n.id,transform:'translate('+p.x+','+p.y+')'});
      var circleAttrs={r:akgRadius(n.type),class:'akg-dot',fill:akgColor(n)};
      var complexityStroke=akgComplexityStroke(n);
      if(complexityStroke){circleAttrs.stroke=complexityStroke.color;circleAttrs['stroke-width']=complexityStroke.width}
      g.appendChild(svgEl('circle',circleAttrs));
      var text=svgEl('text',{x:akgRadius(n.type)+4,y:4,class:'akg-label'});text.textContent=akgLabel(n);
      g.appendChild(text);
      var title=svgEl('title',{});title.textContent=n.name+' ('+n.type+(n.authority?', '+n.authority:'')+')';g.appendChild(title);
      nodeGroup.appendChild(g);
    });
    viewport.appendChild(nodeGroup);
    svg.appendChild(viewport);
    akgWireViewport(svg,viewport,width,height);
    return {svg:svg,truncated:nodes.length>AKG_MAX_NODES};
  }
  function id(value){return document.getElementById(value)}
  function esc(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function token(){return localStorage.getItem('mission_control_token')||''}
  async function post(url,body){var response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});var data=await response.json();if(!response.ok||data.status==='unauthorized')throw new Error(data.error||'Architecture evidence is unavailable.');return data}
  function akgLegend(nodes){
    var types=[];nodes.forEach(function(n){if(!AKG_AUTHORITY_COLOR[n.authority]&&types.indexOf(n.type)<0)types.push(n.type)});
    var authorities=[];nodes.forEach(function(n){if(AKG_AUTHORITY_COLOR[n.authority]&&authorities.indexOf(n.authority)<0)authorities.push(n.authority)});
    var typeItems=types.map(function(t){return '<span class="akg-legend-item"><i style="background:'+(AKG_TYPE_COLOR[t]||'#7dd3fc')+'"></i>'+esc(t)+'</span>'});
    var authorityItems=authorities.map(function(a){return '<span class="akg-legend-item"><i style="background:'+AKG_AUTHORITY_COLOR[a]+'"></i>'+esc(a)+'</span>'});
    var hasFunctions=nodes.some(function(n){return n.type==='Function'});
    var complexityNote=hasFunctions?['<span class="akg-legend-item"><i style="background:linear-gradient(90deg,rgb(56,189,248),rgb(239,68,68))"></i>Function ring: cyclomatic complexity (blue=simple, red=complex)</span>']:[];
    return typeItems.concat(authorityItems).concat(complexityNote).join('');
  }
  function renderGraph(data){
    window.akgCurrent=data;
    var built=akgBuildSvg(data.nodes,data.edges);
    id('akgSummary').textContent=data.nodes.length+' nodes · '+data.edges.length+' typed relationships · '+data.view+' view'+(built.truncated?' (showing first '+AKG_MAX_NODES+' nodes)':'');
    var container=id('akgNodes');
    container.innerHTML='<div class="akg-legend">'+akgLegend(data.nodes.slice(0,AKG_MAX_NODES))+'</div>';
    if(!data.nodes.length){container.innerHTML+='<p class="muted">No nodes match this projection.</p>'}else{container.appendChild(built.svg)}
    id('akgDetail').innerHTML='<p class="muted">Select a component to inspect evidence, dependencies, health, and architectural decisions.</p>';
  }
  function akgControlFlowRows(node){
    var cf=node.control_flow;
    if(!cf)return '';
    if(cf.status==='unavailable')return '<div class="row"><span>Control flow</span><strong>Unavailable</strong></div>';
    var pathLabel=cf.path_count_capped?cf.path_count+'+':cf.path_count;
    return '<div class="row"><span>Cyclomatic complexity</span><strong>'+esc(cf.cyclomatic_complexity)+'</strong></div><div class="row"><span>Decision points</span><strong>'+esc(cf.decision_points)+'</strong></div><div class="row"><span>Structural path count</span><strong>'+esc(pathLabel)+'</strong></div>';
  }
  function renderDetail(node){
    var quality=node.quality||{},operational=node.operational||{},decision=node.decision||{};
    var evidence=(node.evidence||[]).map(function(item){return '<li>'+esc(item.kind||'evidence')+': '+esc(item.source||'unknown')+'</li>'}).join('');
    id('akgDetail').innerHTML='<h3>'+esc(node.name)+'</h3><div class="row"><span>Type</span><strong>'+esc(node.type)+'</strong></div><div class="row"><span>Authority</span><strong>'+esc(node.authority||'Unknown')+'</strong></div><div class="row"><span>Lifecycle</span><strong>'+esc(node.lifecycle||'Unknown')+'</strong></div><div class="row"><span>Health</span><strong>'+esc((node.health||{}).status||'Unknown')+'</strong></div><div class="row"><span>LOC rule</span><strong>'+esc(quality.line_rule||'Not applicable')+'</strong></div><div class="row"><span>Runtime usage</span><strong>'+esc(operational.runtime_usage||'Unknown')+'</strong></div>'+akgControlFlowRows(node)+'<h3>Why it exists</h3><p>'+esc(decision.why_introduced||node.purpose||'No explicit architectural rationale is currently recorded.')+'</p><h3>Decision</h3><p>'+esc(decision.decision||'Derived from current repository and authority evidence.')+'</p><h3>Evidence</h3><ul>'+evidence+'</ul>';
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
    if(window.akgDidPan){window.akgDidPan=false;return}
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
    return (
        "<script>\n(function(){\n"
        + _AKG_LAYOUT_JS + _AKG_COMPLEXITY_JS + _AKG_RENDER_JS + _AKG_STYLE_JS
        + "\n})();\n</script>"
    )
