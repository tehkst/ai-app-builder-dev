"""The Codebase Map viewer: a zoomable map of a client's codebase (app/platform/codebase_map).

The overview shows the app's main parts and the outside services they use; double-click a part to
go inside it (its sub-parts and files, with what uses it on the left and what it relies on on the
right). Lines are imports, web requests matched to endpoints, outside packages and hosts, and the
connections the Cartographer added. Also: a details panel, search, guided flows, a "Start here"
tour, Health marks on the cards, and a switch to technical detail. Inspired by Floorplan (MIT, see
app/platform/codebase_map/LICENSE-floorplan.txt); the layout is a small layered layout of its own.

Two ways to open it: in Mission Control (`render_viewer`: loads the map with the founder's token)
and as a downloaded file for the client (`render_export`: the map embedded, nothing else). Every
string from the map goes through esc() or textContent: names and descriptions are AI-written.
"""
from __future__ import annotations

import json
from html import escape
from typing import Any, Dict

CSS = r"""
:root{--ground:#F6F5F2;--surface:#FFFFFF;--ink:#17181C;--muted:#5E6470;--line:#E3E1DC;--line-soft:#EFEDE8;
--accent:#2648C9;--accent-soft:#EEF1FC;--import:#8A8F99;--http:#2648C9;--ext:#7A4BC2;--extra:#B5630B;
--bad:#8E2318;--bad-bg:#FBE8E5;--warn:#8A4F00;--warn-bg:#FFF4DD;--good:#1E6B3A;--dot:#DDDAD3;--shadow:0 1px 2px rgba(0,0,0,.06),0 2px 8px rgba(0,0,0,.05)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#15161A;--surface:#1F2127;--ink:#ECEDEF;
--muted:#A3A8B3;--line:#33363E;--line-soft:#292B31;--accent:#8EA5FF;--accent-soft:#252C45;--import:#7D8390;--http:#8EA5FF;
--ext:#B99BEA;--extra:#E3A55A;--bad:#FF9C8F;--bad-bg:#3A2220;--warn:#F1C27A;--warn-bg:#3A2E1A;--good:#8FD3A6;--dot:#2A2C33;
--shadow:0 1px 2px rgba(0,0,0,.4)}}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--ground);color:var(--ink);overflow:hidden;
font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.45}
button,input{font:inherit;color:inherit}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.fp{display:flex;flex-direction:column;height:100%}
.fp-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:10px 16px;background:var(--surface);border-bottom:1px solid var(--line)}
.fp-title{display:flex;flex-direction:column;min-width:0;margin-right:auto}
.fp-title strong{font-size:16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-crumbs{font-size:13px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px}
.fp-crumbs button{background:none;border:0;padding:0;color:var(--accent);cursor:pointer}
.fp-crumbs span[aria-current]{color:var(--ink)}
.fp-btn{min-height:36px;padding:6px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);cursor:pointer;white-space:nowrap}
.fp-btn:hover{background:var(--line-soft)}.fp-btn[aria-pressed="true"]{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.fp-btn .n{display:inline-block;min-width:18px;padding:0 5px;margin-left:4px;border-radius:9px;background:var(--bad-bg);color:var(--bad);font-size:12px;font-weight:600}
.fp-search{position:relative}
.fp-search input{min-height:36px;width:220px;max-width:60vw;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--ground)}
.fp-results{position:absolute;right:0;top:40px;width:340px;max-width:90vw;max-height:60vh;overflow:auto;background:var(--surface);
border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);z-index:20;padding:4px;margin:0;list-style:none}
.fp-results button{display:block;width:100%;text-align:left;background:none;border:0;padding:8px 10px;border-radius:6px;cursor:pointer}
.fp-results button:hover,.fp-results button:focus{background:var(--accent-soft)}
.fp-results small{display:block;color:var(--muted);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fp-body{flex:1;display:flex;min-height:0;position:relative}
.fp-canvas{flex:1;position:relative;overflow:hidden;cursor:grab;touch-action:none;
background-image:radial-gradient(var(--dot) 1px,transparent 1px);background-size:18px 18px}
.fp-canvas.dragging{cursor:grabbing}
.fp-world{position:absolute;left:0;top:0;transform-origin:0 0}
.fp-world svg{position:absolute;left:0;top:0;overflow:visible;pointer-events:none}
.fp-intro{position:absolute;left:20px;top:14px;right:20px;max-width:680px;pointer-events:none;z-index:2}
.fp-intro[hidden]{display:none}
.fp-intro small{color:var(--muted);font-size:13px}
.fp-intro h1{margin:0;font-size:24px;letter-spacing:-.01em}
.fp-intro p{margin:4px 0 0;color:var(--muted);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.fp-card{position:absolute;width:228px;height:96px;padding:10px 12px;background:var(--surface);border:1px solid var(--line);
border-radius:12px;box-shadow:var(--shadow);cursor:pointer;display:flex;flex-direction:column;gap:2px;overflow:hidden;
transition:opacity .15s,border-color .15s}
.fp-card:hover{border-color:var(--accent)}
.fp-card.sel{border:2px solid var(--accent);padding:9px 11px}
.fp-card.dim{opacity:.28}.fp-card.lit{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.fp-card.outside{background:var(--ground);border-style:dashed}
.fp-card.external{border-style:dashed}
.fp-card.planned{border-style:dashed}
.fp-card .h{display:flex;align-items:center;gap:6px;font-weight:600;font-size:14px;min-width:0}
.fp-card .h b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600}
.fp-card .ic{flex:none;width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-size:11px;background:var(--accent-soft);color:var(--accent)}
.fp-card .d{font-size:12.5px;color:var(--muted);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.fp-card .p{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-card .f{margin-top:auto;display:flex;gap:6px;font-size:11.5px;color:var(--muted);align-items:center}
.fp-card .f .bad{color:var(--bad);background:var(--bad-bg);border-radius:6px;padding:0 6px;font-weight:600}
.fp-card .f .more{margin-left:auto;color:var(--accent)}
.fp-edge{fill:none;stroke-width:1.6;opacity:.75}
.fp-edge.import{stroke:var(--import)}.fp-edge.http{stroke:var(--http)}.fp-edge.package{stroke:var(--ext);stroke-dasharray:5 4}
.fp-edge.extra{stroke:var(--extra);stroke-dasharray:2 4}.fp-edge.dim{opacity:.08}.fp-edge.lit{opacity:1;stroke-width:2.6}
.fp-edge-label{font-size:11px;fill:var(--muted)}
.fp-pulse{fill:var(--accent)}.fp-flow{fill:none;stroke:var(--accent);stroke-width:3}
.fp-panel{width:360px;max-width:100%;background:var(--surface);border-left:1px solid var(--line);overflow:auto;padding:16px 18px 32px}
.fp-panel[hidden]{display:none}
.fp-panel h2{margin:0 0 4px;font-size:18px}.fp-panel h3{margin:18px 0 6px;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.fp-panel p{margin:6px 0}.fp-panel ul{margin:0;padding:0;list-style:none}
.fp-panel li{padding:4px 0;border-bottom:1px solid var(--line-soft)}
.fp-panel li button{background:none;border:0;padding:0;color:var(--accent);cursor:pointer;text-align:left}
.fp-panel code,.fp-mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12px;color:var(--muted);word-break:break-all}
.fp-panel .tag{display:inline-block;padding:1px 8px;border-radius:10px;background:var(--line-soft);font-size:12px;color:var(--muted);margin-right:4px}
.fp-panel .bad{background:var(--bad-bg);color:var(--bad)}.fp-panel .warn{background:var(--warn-bg);color:var(--warn)}
.fp-close{float:right;background:none;border:0;font-size:20px;line-height:1;cursor:pointer;color:var(--muted);min-width:32px;min-height:32px}
.fp-narrate{position:absolute;left:50%;bottom:18px;transform:translateX(-50%);width:min(620px,calc(100% - 32px));background:var(--surface);
border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:14px 16px;z-index:10}
.fp-narrate[hidden]{display:none}
.fp-narrate small{color:var(--muted)}.fp-narrate h4{margin:2px 0 4px;font-size:15px}.fp-narrate p{margin:0 0 10px}
.fp-narrate .row{display:flex;gap:8px;justify-content:flex-end}
.fp-menu{position:absolute;top:56px;z-index:20;background:var(--surface);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);
padding:6px;min-width:260px;max-width:90vw}
.fp-menu[hidden]{display:none}
.fp-menu button{display:block;width:100%;text-align:left;background:none;border:0;padding:8px 10px;border-radius:6px;cursor:pointer}
.fp-menu button:hover{background:var(--accent-soft)}.fp-menu small{display:block;color:var(--muted)}
.fp-legend{position:absolute;left:16px;bottom:16px;display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted);
background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:6px 10px}
.fp-legend i{display:inline-block;width:18px;height:0;border-top:2px solid;vertical-align:middle;margin-right:4px}
.fp-zoom{position:absolute;right:16px;bottom:16px;display:flex;flex-direction:column;gap:4px}
.fp-zoom button{width:36px;height:36px;border-radius:8px;border:1px solid var(--line);background:var(--surface);cursor:pointer;font-size:16px}
.fp-msg{margin:auto;padding:32px;max-width:520px;text-align:center;color:var(--muted)}
@media (max-width:760px){.fp-panel{position:absolute;right:0;top:0;bottom:0;width:100%;z-index:15}.fp-legend{display:none}
.fp-search input{width:140px}}
"""

BODY = r"""
<div class="fp">
  <header class="fp-bar">
    <div class="fp-title"><strong id="fpName">Codebase Map</strong><nav class="fp-crumbs" id="fpCrumbs" aria-label="Where you are"></nav></div>
    <button type="button" class="fp-btn" id="fpTour">Start here</button>
    <button type="button" class="fp-btn" id="fpFlows" aria-haspopup="true">Flows</button>
    <button type="button" class="fp-btn" id="fpHealth">Health</button>
    <button type="button" class="fp-btn" id="fpTech" aria-pressed="false" title="Show paths, endpoints and technical names">Technical</button>
    <button type="button" class="fp-btn" id="fpExport" hidden>Download for the client</button>
    <div class="fp-search"><input id="fpSearch" type="search" placeholder="Search the map" aria-label="Search the map" autocomplete="off">
      <ul class="fp-results" id="fpResults" hidden></ul></div>
  </header>
  <div class="fp-menu" id="fpFlowMenu" hidden></div>
  <div class="fp-body">
    <div class="fp-canvas" id="fpCanvas" tabindex="0" aria-label="The map. Drag to move, scroll to zoom, double-click a card to go inside it.">
      <div class="fp-intro" id="fpIntro" hidden></div>
      <div class="fp-world" id="fpWorld"></div>
      <div class="fp-legend"><span><i style="border-color:var(--import)"></i>Uses</span><span><i style="border-color:var(--http)"></i>Web requests</span>
        <span><i style="border-color:var(--ext);border-top-style:dashed"></i>Outside service</span><span><i style="border-color:var(--extra);border-top-style:dotted"></i>Other connection</span></div>
      <div class="fp-zoom"><button type="button" id="fpIn" aria-label="Zoom in">+</button><button type="button" id="fpFit" aria-label="Fit to screen">⤢</button><button type="button" id="fpOut" aria-label="Zoom out">−</button></div>
      <div class="fp-narrate" id="fpNarrate" hidden role="region" aria-live="polite"></div>
    </div>
    <aside class="fp-panel" id="fpPanel" hidden></aside>
  </div>
</div>
"""

SCRIPT = r"""
(function(){
  var $=function(id){return document.getElementById(id)};
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  var W=228,H=96,GX=120,GY=26,SIDE=150;
  var ICON={ui:'▣',service:'◆',worker:'⟳',library:'▤',feature:'◇',data:'⛁',config:'⚙',test:'✓',script:'›_',infra:'☁',external:'⬡',file:'▯',folder:'▭'};
  var KIND={ui:'App people use',service:'Server',worker:'Background jobs',library:'Shared code',feature:'Feature',data:'Data',config:'Settings',
    test:'Tests',script:'Scripts',infra:'Hosting and deployment',external:'Outside service'};
  var G=null,META={},S={board:{node:null,folder:null},sel:null,tech:false,marks:{},view:{x:0,y:0,k:1},narr:null,pos:{},items:[]};
  var nodes={},kids={},files={},routes={},fileKids={},links=[];

  // ---- data ----------------------------------------------------------------------------------
  function prepare(){
    G.nodes.forEach(function(n){nodes[n.id]=n;(kids[n.parent||'']=kids[n.parent||'']||[]).push(n.id)});
    G.files.forEach(function(f){files[f.path]=f;(fileKids[f.node]=fileKids[f.node]||[]).push(f.path)});
    G.routes.forEach(function(r){routes[r.key]=r});
    G.links.forEach(function(l){links.push({a:l[0],b:l[1],kind:l[2],label:l[3]||''})});
    (G.edges||[]).forEach(function(e){links.push({a:e.from,b:e.to,kind:'extra',label:e.label||'',desc:e.description||'',ek:e.kind})});
    S.tech=G.audience==='developers';
  }
  function chain(id){var out=[];var seen={};while(id&&nodes[id]&&!seen[id]){seen[id]=1;out.unshift(id);id=nodes[id].parent}return out}
  function ownerOf(ref){if(nodes[ref])return ref;if(files[ref])return files[ref].node;if(routes[ref])return files[routes[ref].file]?files[routes[ref].file].node:null;return null}
  function fileOf(ref){if(files[ref])return ref;if(routes[ref])return routes[ref].file;return null}
  function own(nodeId){return fileKids[nodeId]||[]}
  function folders(nodeId){  // more than 24 files of its own: group them by folder
    var list=own(nodeId);if(list.length<=24)return null;
    var parts=list.map(function(p){return p.split('/')}),common=0;
    while(parts.every(function(x){return x.length>common+1&&x[common]===parts[0][common]}))common++;
    var map={};list.forEach(function(p){var x=p.split('/');var key=x.length>common+1?x.slice(0,common+1).join('/'):'(here)';(map[key]=map[key]||[]).push(p)});
    return Object.keys(map).length>1?map:null}
  function folderOf(nodeId,path){var f=folders(nodeId);if(!f)return null;for(var k in f)if(f[k].indexOf(path)>=0)return k;return null}
  // what stands for `ref` on board b: an id of a card shown there, inside or around it (null: the board itself)
  function itemFor(b,ref){
    if(nodes[ref]&&nodes[ref].kind==='external')return ref;
    var path=fileOf(ref),n=ownerOf(ref);if(!n)return null;
    var c=chain(n);
    if(!b.node)return c[0];
    var i=c.indexOf(b.node);
    if(i>=0&&i<c.length-1)return c[i+1];
    if(i===c.length-1){
      if(!path)return null;
      var fo=folderOf(n,path);
      if(b.folder)return fo===b.folder?path:'dir:'+n+':'+fo;
      return fo?'dir:'+n+':'+fo:path}
    var bc=chain(b.node);
    if(bc.indexOf(n)>=0)return path||null;  // a file of a part this board sits inside
    var k=0;while(k<c.length&&k<bc.length&&c[k]===bc[k])k++;
    return c[k]}
  function insideIds(b){
    if(!b.node)return (kids['']||[]).slice();
    if(b.folder){var fs=folders(b.node);return fs&&fs[b.folder]?fs[b.folder].slice():[]}
    var out=(kids[b.node]||[]).slice(),fo=folders(b.node);
    if(fo)Object.keys(fo).forEach(function(k){out.push('dir:'+b.node+':'+k)});else out=out.concat(own(b.node));
    return out}
  function describe(id){
    if(id.indexOf('dir:')===0){var x=id.split(':'),list=folders(x[1])[x.slice(2).join(':')]||[];
      return {id:id,kind:'folder',label:x.slice(2).join(':').split('/').pop()+'/',sub:list.length+' files',desc:'A folder of '+list.length+' files in '+nodes[x[1]].label+'.',path:x.slice(2).join(':'),files:list}}
    if(nodes[id]){var n=nodes[id];return {id:id,kind:n.kind,label:n.label,desc:n.summary,sub:n.kind==='external'?'Outside service':
      (n.file_count?n.file_count+' file'+(n.file_count===1?'':'s'):'')+((kids[id]||[]).length?' · '+kids[id].length+' parts':''),
      path:(n.paths||[]).join(', '),files:n.kind==='external'?[]:null}}
    var f=files[id];if(!f)return null;
    return {id:id,kind:'file',label:S.tech?f.path.split('/').pop():f.name,desc:f.description,sub:f.lines+' lines'+(f.routes.length?' · '+f.routes.length+' endpoint'+(f.routes.length===1?'':'s'):''),path:f.path,files:[id]}}
  function filesUnder(id){
    if(id.indexOf('dir:')===0)return describe(id).files;if(files[id])return [id];
    var out=[];G.files.forEach(function(f){if(chain(f.node).indexOf(id)>=0)out.push(f.path)});return out}

  // ---- board ---------------------------------------------------------------------------------
  function boardEdges(b,inside){
    var ins={};inside.forEach(function(i){ins[i]=1});
    var agg={},outside={};
    links.forEach(function(l){
      var a=itemFor(b,l.a),c=itemFor(b,l.b);
      if(!a||!c||a===c)return;if(!ins[a]&&!ins[c])return;
      if(!ins[a])outside[a]='left';  // it uses something here
      if(!ins[c]&&!outside[c])outside[c]='right';  // something here relies on it
      var kind=l.kind==='extra'?'extra':l.kind==='package'||(nodes[l.b]&&nodes[l.b].kind==='external')?'package':l.kind;
      var key=a+'>'+c+'>'+kind;var e=agg[key]=agg[key]||{a:a,b:c,kind:kind,n:0,labels:[]};
      e.n++;if(l.label&&e.labels.indexOf(l.label)<0)e.labels.push(l.label)});
    return {edges:Object.keys(agg).map(function(k){return agg[k]}),outside:outside}}
  function layout(inside,edges,isRoot){
    var ins={},out={},indeg={};inside.forEach(function(i){ins[i]=1;out[i]=[];indeg[i]=0});
    edges.forEach(function(e){if(ins[e.a]&&ins[e.b]&&e.a!==e.b){out[e.a].push(e.b)}});
    // break cycles (DFS), then longest-path layers
    var state={},dag={};inside.forEach(function(i){dag[i]=[]});
    function dfs(u){state[u]=1;out[u].forEach(function(v){if(state[v]===1)return;dag[u].push(v);if(!state[v])dfs(v)});state[u]=2}
    inside.slice().sort(function(a,b){return out[b].length-out[a].length}).forEach(function(i){if(!state[i])dfs(i)});
    var rank={};inside.forEach(function(i){rank[i]=0});
    for(var pass=0;pass<inside.length;pass++){var moved=false;
      inside.forEach(function(u){dag[u].forEach(function(v){if(rank[v]<rank[u]+1){rank[v]=rank[u]+1;moved=true}})});if(!moved)break}
    var ext=inside.filter(function(i){return nodes[i]&&nodes[i].kind==='external'});
    var maxr=0;inside.forEach(function(i){if(ext.indexOf(i)<0)maxr=Math.max(maxr,rank[i])});
    ext.forEach(function(i){rank[i]=maxr+1});
    var anyEdge=inside.some(function(i){return out[i].length});
    if(!anyEdge&&inside.length>4){var cols=Math.ceil(Math.sqrt(inside.length*1.6));
      inside.forEach(function(id,i){rank[id]=i%cols})}
    // long edges get a waypoint in every layer they cross, ordered like cards, so they pass between cards
    var way={},items=inside.slice(),DUMMY=34;
    edges.forEach(function(e,ei){if(!ins[e.a]||!ins[e.b])return;var r0=rank[e.a],r1=rank[e.b];if(r1-r0<2)return;
      var pts=[];for(var r=r0+1;r<r1;r++){var d='~'+ei+'~'+r;rank[d]=r;items.push(d);pts.push(d);out[d]=[]}
      way[ei]=pts;var chainIds=[e.a].concat(pts,[e.b]);for(var c=0;c<chainIds.length-1;c++)(out[chainIds[c]]=out[chainIds[c]]||[]).push(chainIds[c+1])});
    var cols2={};items.forEach(function(i){(cols2[rank[i]]=cols2[rank[i]]||[]).push(i)});
    var order=Object.keys(cols2).map(Number).sort(function(a,b){return a-b});
    function name(id){return id.charAt(0)==='~'?'':(describe(id).label||'')}
    order.forEach(function(r){cols2[r].sort(function(a,b){return name(a).localeCompare(name(b))})});
    var idx={};order.forEach(function(r){cols2[r].forEach(function(id,i){idx[id]=i})});
    var preds={};items.forEach(function(i){preds[i]=[];out[i]=out[i]||[]});items.forEach(function(u){out[u].forEach(function(v){if(preds[v])preds[v].push(u)})});
    for(var it=0;it<8;it++){order.forEach(function(r){var nb=it%2?out:preds;
      var bc={};cols2[r].forEach(function(x){var l=nb[x].filter(function(y){return idx[y]!==undefined});
        bc[x]=l.length?l.reduce(function(s,y){return s+idx[y]},0)/l.length:idx[x]});
      cols2[r].sort(function(a,b){return bc[a]-bc[b]||idx[a]-idx[b]});
      cols2[r].forEach(function(id,i){idx[id]=i})})}
    function hgt(id){return id.charAt(0)==='~'?DUMMY:H}
    var heights={},tallest=0;order.forEach(function(r){var h=cols2[r].reduce(function(s,id){return s+hgt(id)+GY},0)-GY;heights[r]=h;tallest=Math.max(tallest,h)});
    var pos={},via={};order.forEach(function(r,ci){var y=(tallest-heights[r])/2;
      cols2[r].forEach(function(id){if(id.charAt(0)==='~')via[id]={x:ci*(W+GX),y:y+DUMMY/2-H/2};else pos[id]={x:ci*(W+GX),y:y};y+=hgt(id)+GY})});
    var routes={};Object.keys(way).forEach(function(ei){routes[ei]=way[ei].map(function(d){return via[d]})});
    return {pos:pos,routes:routes,width:Math.max(1,order.length)*(W+GX)-GX,height:tallest}}

  function render(){
    var b=S.board,inside=insideIds(b),be=boardEdges(b,inside),lay=layout(inside,be.edges,!b.node);
    var left=[],right=[];Object.keys(be.outside).forEach(function(id){(be.outside[id]==='left'?left:right).push(id)});
    var pos=lay.pos;
    function stack(list,x){var h=list.length*(H+GY)-GY,off=(lay.height-h)/2;list.sort().forEach(function(id,i){pos[id]={x:x,y:off+i*(H+GY)}})}
    stack(left,-(W+SIDE));stack(right,lay.width+SIDE);
    S.pos=pos;S.items=Object.keys(pos);S.edges=be.edges;S.inside={};inside.forEach(function(i){S.inside[i]=1});
    var world=$('fpWorld'),html='';
    var intro=$('fpIntro');intro.hidden=!!b.node;
    if(!b.node)intro.innerHTML='<small>Overview · '+esc(G.stats.files)+' files · '+esc(G.stats.routes)+' endpoints</small><h1>'+esc(G.project.name||META.codebase)+'</h1><p>'+esc(G.project.summary)+'</p>';
    S.items.forEach(function(id){var d=describe(id);if(!d)return;var p=pos[id],marks=markCount(id);
      var cls='fp-card'+(S.inside[id]?'':' outside')+(d.kind==='external'?' external':'')+(S.sel===id?' sel':'');
      var canEnter=(nodes[id]&&nodes[id].kind!=='external'&&(nodes[id].file_count>0))||d.kind==='folder';
      html+='<div class="'+cls+'" data-id="'+esc(id)+'" style="left:'+(p.x)+'px;top:'+(p.y)+'px" role="button" tabindex="0" aria-label="'+esc(d.label)+'">'+
        '<div class="h"><span class="ic" aria-hidden="true">'+esc(ICON[d.kind]||'▯')+'</span><b>'+esc(d.label)+'</b></div>'+
        (S.tech&&d.path?'<div class="p">'+esc(d.path)+'</div>':'')+'<div class="d">'+esc(d.desc||'')+'</div>'+
        '<div class="f"><span>'+esc(d.sub||'')+'</span>'+(marks?'<span class="bad">'+marks+' to check</span>':'')+(canEnter&&S.inside[id]?'<span class="more">Open ›</span>':'')+'</div></div>'});
    var svg='<svg width="1" height="1"><defs>'+['import','http','package','extra'].map(function(k){return '<marker id="ar-'+k+'" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--'+(k==='package'?'ext':k)+')"/></marker>'}).join('')+'</defs>';
    be.edges.forEach(function(e,i){var a=pos[e.a],c=pos[e.b];if(!a||!c)return;
      var d=edgePath(a,c,lay.routes[i]);
      svg+='<path class="fp-edge '+e.kind+'" data-e="'+i+'" d="'+d+'" marker-end="url(#ar-'+e.kind+')"><title>'+esc(edgeTitle(e))+'</title></path>'});
    svg+='</svg>';
    world.innerHTML=svg+html;
    crumbs();highlight();
  }
  function edgePath(a,c,via){
    var x1=a.x+W,y1=a.y+H/2,x2=c.x,y2=c.y+H/2;
    if(via&&via.length){var d='M'+x1+' '+y1,px=x1,py=y1;
      via.concat([{x:x2,y:c.y,end:1}]).forEach(function(v){var vy=v.y+H/2,m=(v.x-px)/2;
        d+=' C'+(px+m)+' '+py+' '+(v.x-m)+' '+vy+' '+(v.end?v.x-2:v.x)+' '+vy;if(!v.end){d+=' L'+(v.x+W)+' '+vy;px=v.x+W;py=vy}});
      return d}
    if(x2>x1+10){var m=(x2-x1)/2;return 'M'+x1+' '+y1+' C'+(x1+m)+' '+y1+' '+(x2-m)+' '+y2+' '+(x2-2)+' '+y2}
    if(Math.abs(a.x-c.x)<5){var xs=a.x+W,ys=a.y+H*0.7,xe=c.x+W,ye=c.y+H*0.3;return 'M'+xs+' '+ys+' C'+(xs+70)+' '+ys+' '+(xe+70)+' '+ye+' '+(xe+2)+' '+ye}
    var lift=Math.min(a.y,c.y)-40;return 'M'+(a.x+W/2)+' '+a.y+' C'+(a.x+W/2)+' '+lift+' '+(c.x+W/2)+' '+lift+' '+(c.x+W/2)+' '+(c.y-2)}
  function edgeTitle(e){var A=describe(e.a),B=describe(e.b);
    var verb={import:'uses',http:'sends web requests to',package:'relies on',extra:'connects to'}[e.kind]||'uses';
    return (A?A.label:'')+' '+verb+' '+(B?B.label:'')+(e.n>1?' ('+e.n+' links)':'')+(e.labels.length?': '+e.labels.slice(0,6).join(', '):'')}
  function crumbs(){
    var b=S.board,out=['<button type="button" data-crumb="">Overview</button>'];
    chain(b.node).forEach(function(id,i,all){out.push(i===all.length-1&&!b.folder?'<span aria-current="page">'+esc(nodes[id].label)+'</span>':'<button type="button" data-crumb="'+esc(id)+'">'+esc(nodes[id].label)+'</button>')});
    if(b.folder)out.push('<span aria-current="page">'+esc(b.folder)+'/</span>');
    if(!b.node)out=['<span aria-current="page">Overview</span>'];
    $('fpCrumbs').innerHTML=out.join(' › ')}

  // ---- highlight, selection, panel ---------------------------------------------------------------
  function connected(id){var set={};set[id]=1;(S.edges||[]).forEach(function(e){if(e.a===id)set[e.b]=1;if(e.b===id)set[e.a]=1});return set}
  function highlight(){
    var focus=S.narr&&S.narr.lit?S.narr.lit:S.sel?connected(S.sel):null;
    document.querySelectorAll('.fp-card').forEach(function(el){var id=el.dataset.id;
      el.classList.toggle('dim',!!focus&&!focus[id]);el.classList.toggle('lit',!!(S.narr&&S.narr.lit&&S.narr.lit[id]));el.classList.toggle('sel',S.sel===id)});
    document.querySelectorAll('.fp-edge').forEach(function(el){var e=S.edges[+el.dataset.e];
      var on=focus&&focus[e.a]&&focus[e.b]&&(S.narr&&S.narr.lit?true:(e.a===S.sel||e.b===S.sel));
      el.classList.toggle('dim',!!focus&&!on);el.classList.toggle('lit',!!on)})}
  function markCount(id){if(!Object.keys(S.marks).length)return 0;return filesUnder(id).filter(function(p){return S.marks[p]}).length}
  function list(title,items,fmt){if(!items.length)return '';return '<h3>'+esc(title)+'</h3><ul>'+items.slice(0,40).map(fmt).join('')+(items.length>40?'<li>…and '+(items.length-40)+' more</li>':'')+'</ul>'}
  function refBtn(ref,label){return '<li><button type="button" data-go="'+esc(ref)+'">'+esc(label)+'</button></li>'}
  function rel(id){  // which parts or files this one uses and is used by, across the whole map
    var mine={};filesUnder(id).forEach(function(p){mine[p]=1});if(nodes[id]&&nodes[id].kind==='external')mine[id]=1;
    var uses={},by={};
    links.forEach(function(l){var a=fileOf(l.a)||l.a,c=fileOf(l.b)||l.b;
      if(mine[a]&&!mine[c])uses[c]=(uses[c]||0)+1;if(mine[c]&&!mine[a])by[a]=(by[a]||0)+1});
    function lift(m){var out={};Object.keys(m).forEach(function(r){var key=files[r]&&!files[id]?(chain(files[r].node).slice(-1)[0]||r):r;out[key]=(out[key]||0)+m[r]});
      return Object.keys(out).sort(function(a,b){return out[b]-out[a]})}
    return {uses:lift(uses),by:lift(by)}}
  function label(ref){var d=describe(ref);return d?d.label:ref}
  function showPanel(id){
    var d=describe(id),p=$('fpPanel');if(!d){p.hidden=true;return}
    var html='<button type="button" class="fp-close" id="fpPanelClose" aria-label="Close">×</button><span class="tag">'+esc(d.kind==='file'?'File':d.kind==='folder'?'Folder':KIND[d.kind]||d.kind)+'</span>'+
      '<h2>'+esc(d.kind==='file'?files[id].name:d.label)+'</h2>';
    if(d.kind==='file'){var f=files[id];
      html+='<p class="fp-mono">'+esc(f.path)+'</p><p>'+esc(f.description||'No description yet.')+'</p><p><span class="tag">'+esc(f.language)+'</span><span class="tag">'+esc(f.lines)+' lines</span></p>';
      html+=list('Endpoints',f.routes,function(k){var r=routes[k]||{};return '<li><strong>'+esc(r.name||k)+'</strong><br><code>'+esc(k)+'</code>'+(r.description?'<br>'+esc(r.description):'')+'</li>'});
      if(S.tech&&f.defines&&f.defines.length)html+='<h3>Defines</h3><p class="fp-mono">'+esc(f.defines.join(', '))+'</p>';
      var hm=healthFor(id);if(hm.length)html+=list('Health',hm,function(h){return '<li><span class="tag '+(h.severity==='high'?'bad':'warn')+'">'+esc(h.title)+'</span> '+esc(h.note)+'</li>'});
    }else{
      html+='<p>'+esc(d.desc||'')+'</p>';
      if(nodes[id]&&nodes[id].details)html+=nodes[id].details.split(/\n\s*\n/).map(function(x){return '<p>'+esc(x)+'</p>'}).join('');
      if(d.sub)html+='<p><span class="tag">'+esc(d.sub)+'</span></p>';
      if(S.tech&&d.path)html+='<p class="fp-mono">'+esc(d.path)+'</p>';
      if(nodes[id]&&nodes[id].kind!=='external'||d.kind==='folder')html+='<p><button type="button" class="fp-btn" data-enter="'+esc(id)+'">Look inside</button></p>';
      html+=list('Parts inside',(kids[id]||[]),function(k){return refBtn(k,nodes[k].label)});
    }
    var r=rel(id);
    html+=list('Used by',r.by,function(x){return refBtn(x,label(x))});
    html+=list(d.kind==='external'?'Connects to':'Relies on',r.uses,function(x){return refBtn(x,label(x))});
    if(d.kind!=='file'&&d.kind!=='external'){var fl=filesUnder(id);html+=list('Files ('+fl.length+')',fl,function(x){return refBtn(x,files[x].name+(S.tech?'':' — '+x))})}
    p.innerHTML=html;p.hidden=false;
    $('fpPanelClose').onclick=function(){select(null)}}
  function healthFor(path){var out=[];(G.health||[]).forEach(function(h){h.refs.forEach(function(r){if(r.ref===path)out.push({title:h.title,severity:h.severity,note:r.note})})});return out}
  function select(id){S.sel=id;if(id)showPanel(id);else $('fpPanel').hidden=true;highlight()}

  // ---- navigation ---------------------------------------------------------------------------------
  function boardFor(ref){  // the board that shows `ref` as one of its own cards
    if(nodes[ref])return nodes[ref].kind==='external'||!nodes[ref].parent?{node:null,folder:null}:{node:nodes[ref].parent,folder:null};
    var p=fileOf(ref);if(!p)return {node:null,folder:null};var n=files[p].node;return {node:n,folder:null}}
  function go(b,focusId){S.board=b;S.sel=null;$('fpPanel').hidden=true;render();fit(focusId);if(focusId&&S.pos[focusId])select(focusId)}
  function goTo(ref){var b=boardFor(ref);go(b,itemFor(b,ref))}
  function enter(id){if(id.indexOf('dir:')===0){var x=id.split(':');go({node:x[1],folder:x.slice(2).join(':')})}
    else if(nodes[id]&&nodes[id].kind!=='external')go({node:id,folder:null});else if(files[id])select(id)}
  function apply(){$('fpWorld').style.transform='translate('+S.view.x+'px,'+S.view.y+'px) scale('+S.view.k+')'}
  function fit(focusId){
    var c=$('fpCanvas'),cw=c.clientWidth,ch=c.clientHeight,ids=S.items;if(!ids.length)return;
    var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;ids.forEach(function(id){var p=S.pos[id];x0=Math.min(x0,p.x);y0=Math.min(y0,p.y);x1=Math.max(x1,p.x+W);y1=Math.max(y1,p.y+H)});
    var top=S.board.node?24:130;  // room for the overview's title
    var k=Math.min(1.1,Math.max(0.25,Math.min((cw-48)/(x1-x0),(ch-top-24)/(y1-y0))));
    S.view={k:k,x:(cw-(x1-x0)*k)/2-x0*k,y:top+(ch-top-24-(y1-y0)*k)/2-y0*k};
    if(focusId&&S.pos[focusId]&&k<0.6){var p=S.pos[focusId];k=0.8;S.view={k:k,x:cw/2-(p.x+W/2)*k,y:ch/2-(p.y+H/2)*k}}
    apply()}
  function zoom(f,cx,cy){var c=$('fpCanvas');cx=cx==null?c.clientWidth/2:cx;cy=cy==null?c.clientHeight/2:cy;
    var k=Math.min(2.5,Math.max(0.15,S.view.k*f));S.view.x=cx-(cx-S.view.x)*k/S.view.k;S.view.y=cy-(cy-S.view.y)*k/S.view.k;S.view.k=k;apply()}

  // ---- flows and the tour -------------------------------------------------------------------------
  function lca(a,b){var ca=chain(ownerOf(a)||''),cb=chain(ownerOf(b)||''),k=0;while(k<ca.length&&k<cb.length&&ca[k]===cb[k])k++;return k?ca[k-1]:null}
  function showStep(){
    var N=S.narr,i=N.i,step=N.steps[i],board,lit={};
    if(N.type==='flow'&&i>0){var prev=N.steps[i-1].ref;board={node:lca(prev,step.ref),folder:null};
      if(itemFor(board,prev)===itemFor(board,step.ref)){var n=ownerOf(step.ref);board={node:n,folder:null}}}
    else board=boardFor(step.ref);
    if(nodes[step.ref]&&nodes[step.ref].kind==='external')board={node:N.type==='flow'&&i>0?board.node:null,folder:null};
    S.board=board;S.sel=null;$('fpPanel').hidden=true;render();
    var cur=itemFor(board,step.ref);if(cur)lit[cur]=1;
    if(N.type==='flow'&&i>0){var pv=itemFor(board,N.steps[i-1].ref);if(pv)lit[pv]=1;pulse(pv,cur)}
    N.lit=lit;fit(cur);highlight();
    var box=$('fpNarrate');
    box.innerHTML='<small>'+esc(N.title)+' · '+(i+1)+' of '+N.steps.length+'</small><h4>'+esc(step.title||label(step.ref))+'</h4><p>'+esc(step.note||'')+'</p>'+
      '<div class="row"><button type="button" class="fp-btn" data-n="close">Close</button>'+(i>0?'<button type="button" class="fp-btn" data-n="prev">Back</button>':'')+
      (i<N.steps.length-1?'<button type="button" class="fp-btn" data-n="next" aria-pressed="true">Next</button>':'<button type="button" class="fp-btn" data-n="close" aria-pressed="true">Done</button>')+'</div>';
    box.hidden=false;var nb=box.querySelector('[data-n="next"]')||box.querySelector('[aria-pressed="true"]');if(nb)nb.focus()}
  function pulse(a,b){if(!a||!b||!S.pos[a]||!S.pos[b])return;var svg=document.querySelector('.fp-world svg');if(!svg)return;
    var path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',edgePath(S.pos[a],S.pos[b]));path.setAttribute('class','fp-flow');svg.appendChild(path);
    var dot=document.createElementNS('http://www.w3.org/2000/svg','circle');dot.setAttribute('r','6');dot.setAttribute('class','fp-pulse');svg.appendChild(dot);
    var len=path.getTotalLength(),t0=null;if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches){var e=path.getPointAtLength(len);dot.setAttribute('cx',e.x);dot.setAttribute('cy',e.y);return}
    function frame(ts){if(!dot.isConnected)return;t0=t0||ts;var t=((ts-t0)%1600)/1600,pt=path.getPointAtLength(t*len);dot.setAttribute('cx',pt.x);dot.setAttribute('cy',pt.y);requestAnimationFrame(frame)}requestAnimationFrame(frame)}
  function startNarration(type,title,steps){if(!steps.length)return;S.narr={type:type,title:title,steps:steps,i:0};$('fpFlowMenu').hidden=true;showStep()}
  function stopNarration(){S.narr=null;$('fpNarrate').hidden=true;render()}

  // ---- health ---------------------------------------------------------------------------------------
  function showHealth(){
    var p=$('fpPanel'),items=G.health||[];
    var html='<button type="button" class="fp-close" id="fpPanelClose" aria-label="Close">×</button><h2>Health</h2>'+
      '<p>Problems the automatic scan can see. A quick check, not a security audit.</p>';
    if(!items.length)html+='<p>Nothing found.</p>';
    items.forEach(function(h,i){html+='<h3><span class="tag '+(h.severity==='high'?'bad':'warn')+'">'+esc(h.severity)+'</span> '+esc(h.title)+' ('+esc(h.count)+')</h3><p>'+esc(h.detail)+'</p>'+
      '<p><button type="button" class="fp-btn" data-mark="'+i+'">Show on map</button></p><ul>'+h.refs.slice(0,12).map(function(r){return '<li><button type="button" data-go="'+esc(r.ref)+'">'+esc(files[r.ref]?files[r.ref].name:r.ref)+'</button> <code>'+esc(r.ref)+'</code> '+esc(r.note)+'</li>'}).join('')+'</ul>'});
    if(Object.keys(S.marks).length)html+='<p><button type="button" class="fp-btn" data-mark="clear">Clear the marks</button></p>';
    p.innerHTML=html;p.hidden=false;$('fpPanelClose').onclick=function(){p.hidden=true}}

  // ---- search ------------------------------------------------------------------------------------
  function search(q){
    q=q.trim().toLowerCase();var box=$('fpResults');if(q.length<2){box.hidden=true;return}
    var hits=[];
    G.nodes.forEach(function(n){if((n.label+' '+n.summary).toLowerCase().indexOf(q)>=0)hits.push([n.id,n.label,KIND[n.kind]||n.kind])});
    G.files.forEach(function(f){if((f.name+' '+f.path+' '+(f.description||'')).toLowerCase().indexOf(q)>=0)hits.push([f.path,f.name,f.path])});
    G.routes.forEach(function(r){if((r.key+' '+r.name).toLowerCase().indexOf(q)>=0)hits.push([r.key,r.name,r.key])});
    box.innerHTML=hits.slice(0,14).map(function(h){return '<li><button type="button" data-go="'+esc(h[0])+'">'+esc(h[1])+'<small>'+esc(h[2])+'</small></button></li>'}).join('')||'<li><small style="padding:8px;display:block">Nothing matches.</small></li>';
    box.hidden=false}

  // ---- events --------------------------------------------------------------------------------------
  function wire(){
    var c=$('fpCanvas'),drag=null,pointers={},pinch=null;
    c.addEventListener('pointerdown',function(e){if(e.target.closest('.fp-card,.fp-narrate,.fp-zoom,.fp-legend'))return;
      pointers[e.pointerId]=[e.clientX,e.clientY];c.setPointerCapture(e.pointerId);
      var ids=Object.keys(pointers);
      if(ids.length===2){var a=pointers[ids[0]],b=pointers[ids[1]];pinch={d:Math.hypot(a[0]-b[0],a[1]-b[1])};drag=null}
      else{drag={x:e.clientX,y:e.clientY,vx:S.view.x,vy:S.view.y,moved:false};c.classList.add('dragging')}});
    c.addEventListener('pointermove',function(e){if(!pointers[e.pointerId])return;pointers[e.pointerId]=[e.clientX,e.clientY];
      var ids=Object.keys(pointers);
      if(pinch&&ids.length===2){var a=pointers[ids[0]],b=pointers[ids[1]],d=Math.hypot(a[0]-b[0],a[1]-b[1]),r=c.getBoundingClientRect();
        zoom(d/pinch.d,(a[0]+b[0])/2-r.left,(a[1]+b[1])/2-r.top);pinch.d=d;return}
      if(!drag)return;var dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>3)drag.moved=true;
      S.view.x=drag.vx+dx;S.view.y=drag.vy+dy;apply()});
    function up(e){if(drag&&!drag.moved&&!e.target.closest('.fp-card'))select(null);delete pointers[e.pointerId];drag=null;pinch=null;c.classList.remove('dragging')}
    c.addEventListener('pointerup',up);c.addEventListener('pointercancel',up);
    c.addEventListener('wheel',function(e){e.preventDefault();var r=c.getBoundingClientRect();
      if(e.ctrlKey||e.metaKey||e.deltaMode!==0||Math.abs(e.deltaY)>=40)zoom(Math.exp(-e.deltaY*0.0022),e.clientX-r.left,e.clientY-r.top);
      else{S.view.x-=e.deltaX;S.view.y-=e.deltaY;apply()}},{passive:false});
    $('fpWorld').addEventListener('click',function(e){var card=e.target.closest('.fp-card');if(card)select(card.dataset.id)});
    $('fpWorld').addEventListener('dblclick',function(e){var card=e.target.closest('.fp-card');if(card)enter(card.dataset.id)});
    $('fpWorld').addEventListener('keydown',function(e){var card=e.target.closest('.fp-card');if(!card)return;
      if(e.key==='Enter'){e.preventDefault();if(S.sel===card.dataset.id)enter(card.dataset.id);else select(card.dataset.id)}});
    document.addEventListener('keydown',function(e){if(e.key==='Escape'){if(S.narr)stopNarration();else if(S.sel)select(null);else if(S.board.node)up1()}});
    function up1(){var b=S.board;if(b.folder)go({node:b.node,folder:null},'dir:'+b.node+':'+b.folder);else go({node:nodes[b.node].parent||null,folder:null},b.node)}
    $('fpCrumbs').addEventListener('click',function(e){var bt=e.target.closest('[data-crumb]');if(bt)go({node:bt.dataset.crumb||null,folder:null})});
    document.body.addEventListener('click',function(e){
      var g=e.target.closest('[data-go]');if(g){$('fpResults').hidden=true;goTo(g.dataset.go);return}
      var en=e.target.closest('[data-enter]');if(en){enter(en.dataset.enter);return}
      var mk=e.target.closest('[data-mark]');if(mk){S.marks={};if(mk.dataset.mark!=='clear')G.health[+mk.dataset.mark].refs.forEach(function(r){S.marks[r.ref]=1});
        render();showHealth();return}
      var n=e.target.closest('[data-n]');if(n){if(n.dataset.n==='close')stopNarration();else{S.narr.i+=n.dataset.n==='next'?1:-1;showStep()}return}
      var fl=e.target.closest('[data-flow]');if(fl){var f=G.flows[+fl.dataset.flow];startNarration('flow',f.title,f.steps.map(function(s){return {ref:s.ref,note:s.note}}));return}
      if(!e.target.closest('#fpFlows,#fpFlowMenu'))$('fpFlowMenu').hidden=true;
      if(!e.target.closest('.fp-search'))$('fpResults').hidden=true});
    $('fpTour').onclick=function(){startNarration('tour','Start here',(G.tour||[]).map(function(s){return {ref:s.ref,title:s.title,note:s.note}}))};
    $('fpFlows').onclick=function(){var m=$('fpFlowMenu'),r=$('fpFlows').getBoundingClientRect();
      m.innerHTML=(G.flows||[]).length?G.flows.map(function(f,i){return '<button type="button" data-flow="'+i+'">'+esc(f.title)+'<small>'+esc(f.description||f.steps.length+' steps')+'</small></button>'}).join(''):'<small style="padding:8px;display:block">No flows in this map.</small>';
      m.style.left=Math.max(8,Math.min(r.left,window.innerWidth-280))+'px';m.hidden=!m.hidden};
    $('fpHealth').onclick=showHealth;
    var hn=(G.health||[]).filter(function(h){return h.severity==='high'}).reduce(function(s,h){return s+h.count},0);
    if(hn)$('fpHealth').innerHTML='Health<span class="n">'+hn+'</span>';
    $('fpTech').onclick=function(){S.tech=!S.tech;$('fpTech').setAttribute('aria-pressed',String(S.tech));render();if(S.sel)showPanel(S.sel)};
    $('fpTech').setAttribute('aria-pressed',String(S.tech));
    $('fpSearch').addEventListener('input',function(e){search(e.target.value)});
    $('fpIn').onclick=function(){zoom(1.25)};$('fpOut').onclick=function(){zoom(0.8)};$('fpFit').onclick=function(){fit()};
    window.addEventListener('resize',function(){fit()});
  }
  function start(graph,meta){
    G=graph;META=meta||{};prepare();
    $('fpName').textContent=(META.client?META.client+' · ':'')+(G.project.name||META.codebase||'Codebase Map');
    document.title=(G.project.name||META.codebase||'Codebase')+' · Map';
    wire();go({node:null,folder:null});
    var seen='';try{seen=localStorage.getItem('fp-tour-'+(META.map_id||G.project.name))||''}catch(e){}
    if(!seen&&(G.tour||[]).length){try{localStorage.setItem('fp-tour-'+(META.map_id||G.project.name),'1')}catch(e){}$('fpTour').click()}
  }
  window.FP_START=start;
})();
"""

BOOT = r"""
(function(){
  var token='';try{token=localStorage.getItem('mission_control_token')||''}catch(e){}
  var id=new URLSearchParams(location.search).get('id')||'';
  function fail(text){document.querySelector('.fp-body').innerHTML='<p class="fp-msg">'+text.replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]})+'</p>'}
  if(!token){location.replace('/mission-control/ui');return}
  fetch('/mission-control/clients/map-data',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token,map_id:id})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.status==='unauthorized'){location.replace('/mission-control/ui');return}
      if(d.error||!d.graph){fail(d.error||'This map could not be loaded.');return}
      var ex=document.getElementById('fpExport');ex.hidden=false;
      ex.onclick=async function(){
        var health=window.confirm('Include the Health list in the copy for the client?\n\nIt shows where passwords or keys sit in the code (never their values). Only include it for people you trust. OK includes it; Cancel leaves it out.');
        var r=await fetch('/mission-control/clients/map-export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token,map_id:id,include_health:health})});
        if(!r.ok){window.alert('The map could not be downloaded.');return}
        var name=((r.headers.get('Content-Disposition')||'').match(/filename="([^"]+)"/)||[])[1]||'map.html';
        var url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
        setTimeout(function(){URL.revokeObjectURL(url)},1000)};
      window.FP_START(d.graph,d.meta)})
    .catch(function(){fail('This map could not be loaded. Is Mission Control running?')});
})();
"""


def _page(title: str, tail: str) -> str:
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<meta name=\"robots\" content=\"noindex\"><title>{escape(title)}</title><style>{CSS}</style></head><body>{BODY}"
            f"<script>{SCRIPT}</script>{tail}</body></html>")


def render_viewer() -> str:
    return _page("Codebase Map", f"<script>{BOOT}</script>")


def _embed(value: Any) -> str:
    """JSON safe to put inside a <script> element (no `</script>` or comment openers can break out)."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") \
        .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def render_export(graph: Dict[str, Any], meta: Dict[str, Any]) -> str:
    title = f"{graph.get('project', {}).get('name') or meta.get('codebase') or 'Codebase'} · Map"
    return _page(title, f"<script>window.FP_START({_embed(graph)},{_embed(meta)});</script>")
