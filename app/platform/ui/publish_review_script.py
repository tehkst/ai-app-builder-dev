from __future__ import annotations

PUBLISH_REVIEW_CARD = """<div class="card" id="publishReviewCard">
<h2>Publish requests</h2>
<p class="muted">Completed customer builds waiting for a founder decision before anything goes live.</p>
<div class="actions"><button class="secondary" id="publishReviewRefreshBtn">Refresh</button></div>
<div id="publishReviewList" class="publish-review-list"><p class="muted">Loading...</p></div>
</div>
<style>
.publish-review-list{display:grid;gap:10px;margin-top:12px}
.publish-review-item{border:1px solid var(--line);border-radius:12px;padding:14px;background:#07101e}
.publish-review-item h3{margin:0 0 4px;font-size:16px}
.publish-review-meta{display:flex;flex-wrap:wrap;gap:10px;font-size:12px;color:var(--muted);margin-bottom:8px}
.publish-review-sow{max-height:120px;overflow:auto;white-space:pre-wrap;font-size:13px;color:#dbeafe;background:#050b15;border-radius:8px;padding:10px;margin-bottom:10px}
.publish-review-actions{display:flex;gap:8px}
.publish-review-empty{padding:14px;color:var(--muted)}
</style>"""


def render_publish_review_script() -> str:
    return r"""<script>
(function(){
  function id(value){return document.getElementById(value)}
  function esc(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function token(){return localStorage.getItem('mission_control_token')||''}
  async function post(url,body){var response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({token:token()},body||{}))});var data=await response.json().catch(function(){return {status:'error',error:'The service returned an unreadable response.'}});if(!response.ok||data.status==='unauthorized')throw new Error(data.error||'Publish review is unavailable.');return data}
  function buildLabel(build,buildCompleted){if(!build)return'No build linked yet';return(buildCompleted?'Build complete':'Build '+esc(build.status||'in progress'))+' · '+esc(build.completed_step_count||0)+'/'+esc(build.step_count||0)+' steps'}
  function itemCard(item){
    var actionsHtml='';
    if(item.publish_status==='requested'){
      actionsHtml='<button class="primary" data-approve="'+esc(item.scoping_request_id)+'">Approve</button><button class="secondary" data-reject="'+esc(item.scoping_request_id)+'">Reject</button>';
    }else if(item.publish_status==='approved'){
      actionsHtml='<span class="tag">Approved</span><button class="primary" data-materialize="'+esc(item.scoping_request_id)+'">Create PR</button>';
    }else if(item.publish_status==='pr_created'){
      actionsHtml='<span class="tag">PR open'+(item.publish_pull_request_url?': <a href="'+esc(item.publish_pull_request_url)+'" target="_blank" rel="noreferrer">'+esc(item.publish_pull_request_url)+'</a>':'')+'</span><button class="primary" data-deploy="'+esc(item.scoping_request_id)+'" data-app-id="'+esc(item.publish_app_id)+'">Deploy to Cloud Run</button>';
    }
    return '<div class="publish-review-item" data-item="'+esc(item.scoping_request_id)+'">'
      +'<h3>'+esc(item.project_name)+'</h3>'
      +'<div class="publish-review-meta"><span>Owner: '+esc(item.owner)+'</span><span>Requested: '+esc(item.publish_requested_at||'unknown')+'</span><span>'+buildLabel(item.build,item.build_completed)+'</span>'+(item.build_completed?'':'<span class="warn">Build not completed — review before approving</span>')+'</div>'
      +'<div class="publish-review-sow">'+esc(item.scope_of_work_markdown||'No scope of work recorded.')+'</div>'
      +'<div class="publish-review-actions">'+actionsHtml+'</div>'
      +'<div class="muted" id="publishReviewResult-'+esc(item.scoping_request_id)+'"></div>'
      +'</div>';
  }
  async function loadPublishRequests(){
    var list=id('publishReviewList');if(!list)return;
    list.innerHTML='<p class="muted">Loading...</p>';
    try{
      var data=await post('/mission-control/publish-requests/list',{});
      var items=data.requests||[];
      list.innerHTML=items.length?items.map(itemCard).join(''):'<p class="publish-review-empty">No publish requests are waiting for review.</p>';
      bindActions();
    }catch(error){
      list.innerHTML='<p class="publish-review-empty">'+esc(error.message||String(error))+'</p>';
    }
  }
  function bindActions(){
    document.querySelectorAll('[data-approve]').forEach(function(button){
      button.onclick=function(){decide(button,button.dataset.approve,'approve')};
    });
    document.querySelectorAll('[data-reject]').forEach(function(button){
      button.onclick=function(){decide(button,button.dataset.reject,'reject')};
    });
    document.querySelectorAll('[data-materialize]').forEach(function(button){
      button.onclick=function(){materialize(button,button.dataset.materialize)};
    });
    document.querySelectorAll('[data-deploy]').forEach(function(button){
      button.onclick=function(){deployApp(button,button.dataset.deploy,button.dataset.appId)};
    });
  }
  async function deployApp(button,scopingRequestId,appId){
    var result=id('publishReviewResult-'+scopingRequestId);
    if(!appId){if(result)result.textContent='No app id is recorded for this request yet.';return}
    if(!confirm('This deploys generated_apps/'+appId+' as Cloud Run service "'+appId+'". Make sure the pull request has already been merged into main first - deploying before merge will deploy whatever generated_apps/'+appId+' currently contains on main. Continue?'))return;
    var phrase=prompt('Type the exact approval phrase to confirm:\n\nI APPROVE CLOUD RUN DEPLOYMENT');
    if(phrase!=='I APPROVE CLOUD RUN DEPLOYMENT'){if(result)result.textContent='Approval phrase did not match, so nothing was deployed.';return}
    button.disabled=true;
    if(result)result.textContent='Deploying... this can take a minute or two.';
    try{
      var data=await post('/mission-control/deployment/execute',{service_name:appId,source_directory:'generated_apps/'+appId,approval_phrase:phrase,live_execution:true});
      if(data.status!=='deployment-completed'){
        if(result)result.textContent=data.recommended_action||(data.summary||'').slice(-500)||('Deployment did not complete (status: '+data.status+').');
        button.disabled=false;
        return;
      }
      if(data.service_url){
        await markPublishRequestLive(scopingRequestId,data.service_url);
        if(result)result.innerHTML='Live: <a href="'+esc(data.service_url)+'" target="_blank" rel="noreferrer">'+esc(data.service_url)+'</a>';
        await loadPublishRequests();
      }else if(result){
        result.textContent='Deployed (revision '+esc(data.revision_name||'unknown')+'), but no service URL was returned - check the Cloud Run console and record the live URL manually.';
      }
    }catch(error){
      if(result)result.textContent=error.message||String(error);
      button.disabled=false;
    }
  }
  async function markPublishRequestLive(scopingRequestId,liveUrl){
    try{
      await post('/mission-control/publish-requests/mark-live',{scoping_request_id:scopingRequestId,live_url:liveUrl});
    }catch(error){
      var result=id('publishReviewResult-'+scopingRequestId);
      if(result)result.textContent='Deployed to '+liveUrl+', but could not record it as live for the customer: '+(error.message||error)+'. Retry from here or note it manually.';
    }
  }
  async function materialize(button,scopingRequestId){
    var result=id('publishReviewResult-'+scopingRequestId);
    var phrase=prompt('This creates a real pull request against generated_apps/<app-id>/ for founder review. Type the exact approval phrase to confirm:\n\nI APPROVE GITHUB EXECUTION');
    if(phrase!=='I APPROVE GITHUB EXECUTION'){if(result)result.textContent='Approval phrase did not match, so no pull request was created.';return}
    button.disabled=true;
    if(result)result.textContent='Creating pull request...';
    try{
      var data=await post('/mission-control/publish-requests/materialize',{scoping_request_id:scopingRequestId,approval_phrase:phrase,live_execution:true});
      if(data.status!=='pull-request-created'){
        if(result)result.textContent=data.error||('Could not create the pull request (status: '+data.status+').');
        button.disabled=false;
        return;
      }
      await loadPublishRequests();
    }catch(error){
      if(result)result.textContent=error.message||String(error);
      button.disabled=false;
    }
  }
  async function decide(button,scopingRequestId,action){
    var result=id('publishReviewResult-'+scopingRequestId);
    if(action==='reject'&&!confirm('Reject this publish request? The customer will see it was declined.'))return;
    button.disabled=true;
    var siblings=button.parentElement?button.parentElement.querySelectorAll('button'):[];
    siblings.forEach(function(sibling){sibling.disabled=true});
    if(result)result.textContent=action==='approve'?'Approving...':'Rejecting...';
    try{
      var data=await post('/mission-control/publish-requests/'+action,{scoping_request_id:scopingRequestId});
      if(data.status!=='approved'&&data.status!=='rejected'){
        if(result)result.textContent=data.error||('Could not '+action+' this request.');
        siblings.forEach(function(sibling){sibling.disabled=false});
        return;
      }
      await loadPublishRequests();
    }catch(error){
      if(result)result.textContent=error.message||String(error);
      siblings.forEach(function(sibling){sibling.disabled=false});
    }
  }
  document.addEventListener('DOMContentLoaded',function(){
    if(id('publishReviewRefreshBtn'))id('publishReviewRefreshBtn').addEventListener('click',loadPublishRequests);
    var nav=document.querySelector('[data-section="deployments"]');
    if(nav)nav.addEventListener('click',loadPublishRequests);
    if(window.location.hash==='#deployments')loadPublishRequests();
  });
  window.loadPublishRequests=loadPublishRequests;
})();
</script>"""
