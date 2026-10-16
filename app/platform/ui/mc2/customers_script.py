"""Mission Control v2 Customers (stage 2): business numbers, publish decisions, all customers.

Data: GET /mission-control/business-metrics (customers, sign-ups, MRR), POST
/mission-control/customers/list (customers joined with their apps) and the publish-review API
(/mission-control/publish-requests/*). Publishing keeps the classic safeguards: approving only
records the decision; opening the pull request needs the typed "I APPROVE GITHUB EXECUTION"
phrase; sending back asks first. Deploying is not offered here: there is no host yet (see
CLAUDE.md). Every server string goes through esc().
"""
from __future__ import annotations

CUSTOMERS_SCRIPT = r"""
(function(){
  var MC=window.MC;var esc=MC.esc;var $=function(id){return document.getElementById(id)};
  var appOwner={};
  MC.customerFor=function(scopingId){return appOwner[scopingId]||''};
  function tag(label,tone){return '<span class="mc-tag '+tone+'">'+esc(label)+'</span>'}
  function day(iso){var d=new Date(iso);return isNaN(d)?'—':d.toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'})}
  function metric(claim,format){if(!claim||claim.value==null)return '—';return format?format(claim.value):String(claim.value)}
  function money(cents){return (cents/100).toLocaleString(undefined,{style:'currency',currency:'USD',maximumFractionDigits:0})}
  var TONE={'live':'done','published, PR open':'run','waiting to publish':'needs','publish declined':'stuck','building':'run','scoping':'plain',
    'built, not published':'plain','build failed':'stuck','blocked':'stuck','cancelled':'plain','build status unknown':'plain'};
  function ownerMap(c){var m={};c.customers.forEach(function(r){r.apps.forEach(function(a){if(a.scoping_request_id)m[a.scoping_request_id]=r.name})});return m}

  function renderMetrics(m,c){
    var cards=[['Customers',metric(m&&m.customers)],['Sign-ups, last 30 days',metric(m&&m.signups_last_30d)],
      ['Monthly revenue',metric(m&&m.mrr_cents,money)],['Apps being built',c&&c.status==='ready'?String(c.apps_being_built):'—']];
    $('mcMetrics').innerHTML=cards.map(function(x){return '<div class="mc-card mc-metric"><span>'+esc(x[0])+'</span><strong>'+esc(x[1])+'</strong></div>'}).join('');
  }
  function publishCard(r){
    var id=esc(r.scoping_request_id),who=MC.customerFor(r.scoping_request_id)||'A customer';
    var build=r.publish_status==='approved'?'You approved publishing. Next, open the pull request so the code is reviewed before anything goes out.'
      :r.build_completed?'Build finished and checked.':'The build has not finished yet. Review it before you approve.';
    var actions=r.publish_status==='requested'
      ?'<button type="button" class="mc-btn" data-publish="approve" data-id="'+id+'">Approve publishing</button><button type="button" class="mc-btn secondary" data-publish="reject" data-id="'+id+'">Send back</button>'
      :'<span class="mc-tag needs">Approved</span><button type="button" class="mc-btn" data-publish="materialize" data-id="'+id+'">Open the pull request</button>';
    return '<div class="mc-card mc-decision"><div class="mc-text">'+tag(r.publish_status==='requested'?'Waiting for you':'Approved — next step','needs')+
      '<h3>'+esc(who)+' · '+esc(r.project_name)+'</h3><p>'+esc(build)+' Nothing goes live for the customer until you say so.</p>'+
      '<details><summary>What they asked for</summary><pre>'+esc(r.scope_of_work_markdown||'No scope recorded.')+'</pre></details>'+
      '<p class="mc-result" id="mcPub-'+id+'" aria-live="polite"></p></div><div class="mc-actions">'+actions+'</div></div>';
  }
  function renderPublish(p){
    var box=$('mcPublish');
    if(!p||p.status!=='ready'){box.innerHTML='<p class="mc-empty">Publish requests could not be loaded'+(p&&p.error?': '+esc(p.error):'.')+'</p>';return}
    var items=p.requests||[];
    box.innerHTML=items.length?items.map(publishCard).join(''):'<p class="mc-empty">No customer is waiting for you to publish.</p>';
  }
  function renderCustomers(c){
    var box=$('mcCustomerTable');
    if(!c||c.status!=='ready'){box.innerHTML='<p class="mc-empty">Customers could not be loaded'+(c&&c.error?': '+esc(c.error):'.')+'</p>';return}
    if(!c.customers.length){box.innerHTML='<p class="mc-empty">No customers yet. They sign up and build through the Customer Portal.</p>';return}
    box.innerHTML='<table class="mc-table"><thead><tr><th scope="col">Customer</th><th scope="col">Apps</th><th scope="col">Plan</th><th scope="col">Last activity</th></tr></thead><tbody>'+
      c.customers.map(function(r){
        var apps=r.apps.length?r.apps.map(function(a){var link=a.live_url||a.pull_request_url;
          return '<div class="mc-app-line">'+(link?'<a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">'+esc(a.name)+'</a>':esc(a.name))+' '+tag(a.stage,TONE[a.stage]||'plain')+'</div>'}).join(''):'<span class="mc-empty">No apps yet</span>';
        return '<tr><th scope="row">'+esc(r.name)+'<small>'+esc(r.member_count)+' '+(r.member_count===1?'person':'people')+' · since '+esc(day(r.created_at))+'</small></th><td>'+apps+'</td><td>'+esc(r.plan||'—')+'</td><td>'+esc(day(r.last_activity))+'</td></tr>'}).join('')+'</tbody></table>'+
      (c.apps_without_customer?'<p class="mc-empty">'+esc(c.apps_without_customer)+' app request(s) could not be matched to a customer.</p>':'');
  }

  async function load(){
    var res=await Promise.allSettled([fetch('/mission-control/business-metrics').then(function(r){return r.json()}),
      MC.post('/mission-control/customers/list'),MC.post('/mission-control/publish-requests/list')]);
    var val=function(i){return res[i].status==='fulfilled'?res[i].value:{status:'error',error:res[i].reason&&res[i].reason.message}};
    var c=val(1);appOwner=c.status==='ready'?ownerMap(c):{};
    renderMetrics(val(0),c);renderPublish(val(2));renderCustomers(c);
  }
  MC.onShow=MC.onShow||{};MC.onShow.customers=load;

  async function act(btn){
    var id=btn.dataset.id,kind=btn.dataset.publish,out=$('mcPub-'+id),body={scoping_request_id:id};
    if(kind==='reject'&&!window.confirm('Send this back? The customer will see it was declined and can ask again.'))return;
    if(kind==='materialize'){var p=window.prompt('This opens a real pull request with the customer’s app for review. Type the exact approval phrase to confirm:\n\nI APPROVE GITHUB EXECUTION');
      if(p!=='I APPROVE GITHUB EXECUTION'){out.textContent='The approval phrase did not match, so nothing was done.';return}
      body.approval_phrase=p;body.live_execution=true}
    var ok={approve:'approved',reject:'rejected',materialize:'pull-request-created'}[kind];
    btn.disabled=true;out.textContent='Working…';
    try{var d=await MC.post('/mission-control/publish-requests/'+kind,body);
      if(d.status!==ok){out.textContent=d.error||('That did not complete (status: '+d.status+').');btn.disabled=false;return}
      await load();if(MC.refreshHome)MC.refreshHome();
    }catch(e){out.textContent=e.message;btn.disabled=false}
  }
  document.addEventListener('click',function(e){var b=e.target.closest('[data-publish]');if(b)act(b)});
  if(MC.token())MC.post('/mission-control/customers/list').then(function(c){if(c.status==='ready')appOwner=ownerMap(c)}).catch(function(){});
})();
"""
