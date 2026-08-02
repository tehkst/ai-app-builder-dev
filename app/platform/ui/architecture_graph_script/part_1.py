from __future__ import annotations


# Node-link diagram: deterministic (no Math.random, so a reload doesn't jitter the
# layout) force-directed placement computed once per render, then drawn as static
# SVG - no continuous physics loop, so it never spins the CPU while idle.
_AKG_LAYOUT_JS = r"""
  var AKG_TYPE_COLOR={Module:'#38bdf8',Service:'#a78bfa',Artifact:'#fbbf24',Mission:'#34d399',Workflow:'#60a5fa',Agent:'#f472b6',Provider:'#fb923c',Technology:'#94a3b8',Runtime:'#22d3ee',Deployment:'#f87171',Class:'#c084fc',Function:'#86efac'};
  // Richer classification (node_classification.py) - colored distinctly so these
  // read as a real signal, not just "not a service.py" (the old two-bucket
  // Canonical/Adapter split). Nodes classified only as Canonical/Adapter/Unknown
  // fall back to the plain type-based palette above - no bad-fit color forced.
  var AKG_AUTHORITY_COLOR={'Gate/Guard':'#f43f5e','Router/Orchestrator':'#8b5cf6','Trigger/Event':'#10b981','Connector/Protocol':'#f59e0b','Attestation/Proof':'#06b6d4','Stub':'#ef4444','Entry Point':'#eab308'};
  var AKG_TYPE_RADIUS={Service:9,Runtime:9,Deployment:8,Mission:8,Provider:7,Technology:7,Agent:6,Workflow:6,Artifact:6,Module:5,Class:5,Function:3};
  var AKG_MAX_NODES=160;
  function akgHash(s){var h=0;for(var i=0;i<s.length;i++){h=(h*31+s.charCodeAt(i))|0}return Math.abs(h)}
  function akgColor(node){return AKG_AUTHORITY_COLOR[node.authority]||AKG_TYPE_COLOR[node.type]||'#7dd3fc'}
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

# Second visual channel (SVG stroke, not fill) for Function-node complexity: fill
# color already carries authority/type meaning (akgColor above), and Gate/Guard,
# Router/Orchestrator, and Stub authorities - exactly the functions most worth
# flagging as complex - take priority in that lookup, so a complexity score
# competing in the same fill-color chain would never show for them. A separate
# stroke scale avoids that collision entirely. Clamped at cyclomatic_complexity=21
# as "very complex" - a visual scale choice, not a claimed fact about the code.
_AKG_COMPLEXITY_JS = r"""
  function akgComplexityStroke(node){
    var cf=node.control_flow;
    if(node.type!=='Function'||!cf||cf.cyclomatic_complexity==null)return null;
    var t=Math.max(0,Math.min(1,(cf.cyclomatic_complexity-1)/20));
    var r=Math.round(56+(239-56)*t),g=Math.round(189-(189-68)*t),b=Math.round(248-(248-68)*t);
    return {color:'rgb('+r+','+g+','+b+')',width:1+t*2.5};
  }
"""
