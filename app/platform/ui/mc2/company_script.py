"""Mission Control v2 Company (stage 3): the AI team and who is next to hire.

Data: POST /mission-control/orca/workforce ({team, planned}), read from company/workforce. The
"How work gets done" steps and Insights links are static markup in page.py. Every server string
goes through esc().
"""
from __future__ import annotations

COMPANY_SCRIPT = r"""
(function(){
  var MC=window.MC;var esc=MC.esc;var $=function(id){return document.getElementById(id)};
  var ROLE={planner:['plans','run'],builder:['builds','done'],reviewer:['checks','needs'],specialist:['specialist','plain']};
  function card(name,label,tone,text){return '<li class="mc-card mc-person"><div class="mc-person-head"><h3>'+esc(name)+'</h3><span class="mc-tag '+tone+'">'+esc(label)+'</span></div><p>'+esc(text)+'</p></li>'}
  async function load(){
    var box=$('mcTeam');
    try{var d=await MC.post('/mission-control/orca/workforce');
      var team=(d.team||[]).map(function(e){var r=ROLE[e.role]||ROLE.specialist;return card(e.name,r[0],r[1],e.summary)});
      var next=(d.planned||[]);
      if(next.length)team.push('<li class="mc-card mc-person mc-planned"><div class="mc-person-head"><h3>Next to hire</h3><span class="mc-tag">planned</span></div><ul>'+
        next.map(function(p){return '<li><strong>'+esc(p.name)+'</strong> — '+esc(p.why)+'</li>'}).join('')+'</ul></li>');
      box.innerHTML=team.join('')||'<li class="mc-empty">No one on the team yet.</li>';
    }catch(e){box.innerHTML='<li class="mc-empty">The team could not be loaded: '+esc(e.message)+'</li>'}
  }
  MC.onShow=MC.onShow||{};MC.onShow.company=load;
})();
"""
