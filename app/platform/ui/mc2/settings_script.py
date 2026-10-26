"""Mission Control v2 Settings (stage 4): the classic controls, grouped into AI, Email, GitHub,
Credentials and Deployment.

Endpoints are the classic ones: /mission-control/runtime/{ai-provider,smtp-provider,
independent-review} (reads public, saves founder-only), /mission-control/credentials/*,
/mission-control/github/health, /mission-control/repo-import/* and /mission-control/auth/logout.
Secret values are never put in the page except when the founder clicks Reveal (after a confirm);
they are hidden again after 30 seconds. Every server string goes through esc().
"""
from __future__ import annotations

SETTINGS_SCRIPT = r"""
(function(){
  var MC=window.MC;var esc=MC.esc;var $=function(id){return document.getElementById(id)};
  function get(url){return fetch(url).then(function(r){return r.json()})}
  function say(id,text,bad){var el=$(id);el.textContent=text;el.classList.toggle('bad',!!bad)}
  function opts(list,current){return list.map(function(o){return '<option value="'+esc(o[0])+'"'+(o[0]===current?' selected':'')+'>'+esc(o[1])+'</option>'}).join('')}
  var LABEL={openai:'OpenAI',deepseek:'DeepSeek'};var ai=null;

  async function loadAi(){
    try{ai=await get('/mission-control/runtime/ai-provider');
      $('mcAiProvider').innerHTML=opts(Object.keys(ai.supported_models||{}).map(function(k){return [k,LABEL[k]||k]}),ai.provider);
      fillModels(ai.model);
      say('mcAiStatus',(LABEL[ai.provider]||ai.provider)+' · '+ai.model+' — '+(ai.api_key_present?'API key is set.':'API key is missing: add it under Credentials.'),!ai.api_key_present);
    }catch(e){say('mcAiStatus','Could not read the AI setting: '+e.message,true)}
    try{var r=await get('/mission-control/runtime/independent-review');$('mcReview').value=r.enabled?'on':'off'}catch(e){}
  }
  function fillModels(current){var models=(ai&&ai.supported_models||{})[$('mcAiProvider').value]||[];$('mcAiModel').innerHTML=opts(models.map(function(m){return [m,m]}),current)}
  async function loadEmail(){
    try{var d=await get('/mission-control/runtime/smtp-provider');var p=d.available_providers||{};
      $('mcEmailProvider').innerHTML=opts(Object.keys(p).map(function(k){return [k,p[k].label||k]}),d.provider);
      say('mcEmailStatus',((p[d.provider]||{}).label||d.provider)+' — '+(d.status==='configured'?'password is set.':'password is missing: add it under Credentials.'),d.status!=='configured');
    }catch(e){say('mcEmailStatus','Could not read the email setting: '+e.message,true)}
  }
  async function save(url,body,statusId,reload){
    say(statusId,'Saving…');
    try{var d=await MC.post(url,body);if(d.error||d.status==='invalid-request')throw new Error(d.error||'Not saved.');say(statusId,'Saved.');setTimeout(reload,600)}
    catch(e){say(statusId,'Not saved: '+e.message,true)}
  }

  async function loadCredentials(){
    var box=$('mcCreds');
    try{var d=await MC.post('/mission-control/credentials/list');
      var note=d.vault_configured?(d.vault_mode==='local'?'<p class="mc-empty">Keys you save here are encrypted in the database with a master key kept on this Mac (vault.key, readable only by you). They take priority over keys in ai-keys.env.</p>':''):'<p class="mc-empty">Encryption isn’t set up on this server (KMS_KEY_NAME), so keys can’t be saved here yet. Keys set as environment variables still work.</p>';
      box.innerHTML=note+'<ul class="mc-rows">'+(d.credentials||[]).map(function(c){
        var state=c.configured?'<span class="mc-tag done">Set'+(c.source==='environment'?' (environment)':(c.source==='vault'?' (saved here)':''))+'</span>':'<span class="mc-tag stuck">Missing</span>';
        return '<li><div><strong>'+esc(c.display_name)+'</strong>'+(c.configured?'<small>'+esc(c.masked_value)+'</small>':'')+'<small class="mc-secret" id="mcSecret-'+esc(c.key_name)+'"></small></div>'+
          '<div class="mc-actions">'+state+(c.source==='vault'?'<button type="button" class="mc-btn quiet" data-reveal="'+esc(c.key_name)+'">Reveal</button>':'')+
          (d.vault_configured?'<button type="button" class="mc-btn secondary" data-replace="'+esc(c.key_name)+'">'+(c.configured?'Replace':'Add')+'</button>':'')+'</div>'+
          '<form class="mc-inline" data-save="'+esc(c.key_name)+'" hidden><label class="mc-sr" for="mcNew-'+esc(c.key_name)+'">New value for '+esc(c.display_name)+'</label>'+
          '<input type="password" id="mcNew-'+esc(c.key_name)+'" autocomplete="off" placeholder="Paste the new value"><button type="submit" class="mc-btn">Save</button></form></li>'}).join('')+'</ul>';
    }catch(e){box.innerHTML='<p class="mc-empty">Credentials could not be loaded: '+esc(e.message)+'</p>'}
  }
  async function credentialAction(e){
    var t=e.target;
    if(t.dataset.replace){var f=document.querySelector('[data-save="'+t.dataset.replace+'"]');f.hidden=!f.hidden;if(!f.hidden)f.querySelector('input').focus();return}
    if(t.dataset.reveal){if(!window.confirm('Show this secret on screen for 30 seconds?'))return;var out=$('mcSecret-'+t.dataset.reveal);
      try{var d=await MC.post('/mission-control/credentials/reveal',{key_name:t.dataset.reveal});out.textContent=d.value||d.error||'Not available.';setTimeout(function(){out.textContent=''},30000)}
      catch(err){out.textContent=err.message}}
  }
  async function credentialSave(e){
    var f=e.target.closest('[data-save]');if(!f)return;e.preventDefault();var input=f.querySelector('input');var value=input.value;if(!value)return;
    input.value='';f.querySelector('button').disabled=true;
    try{var d=await MC.post('/mission-control/credentials/save',{key_name:f.dataset.save,value:value});if(d.status!=='saved')throw new Error(d.error||d.status);await loadCredentials();if(f.dataset.save.indexOf('API_KEY')>0)loadAi()}
    catch(err){f.querySelector('button').disabled=false;window.alert('Not saved: '+err.message)}
  }

  async function checkGithub(){
    say('mcGithubStatus','Checking…');
    try{var d=await MC.post('/mission-control/github/health');
      say('mcGithubStatus',d.connected?'Connected to '+d.repository+'.':(d.status==='github-missing-token'?'No GitHub token: add it under Credentials.':'Partly connected to '+(d.repository||'GitHub')+'. Some checks failed.'),!d.connected)}
    catch(e){say('mcGithubStatus','Check failed: '+e.message,true)}
  }
  async function loadRepos(){
    var box=$('mcRepos');
    try{var d=await MC.post('/mission-control/repo-import/list');var rows=d.repositories||[];
      box.innerHTML=rows.length?'<ul class="mc-rows">'+rows.map(function(r){return '<li><div><strong>'+esc(r.full_name)+'</strong><small>'+esc(r.status)+(r.last_error?' · '+esc(r.last_error):'')+'</small></div><button type="button" class="mc-btn quiet" data-remove-repo="'+esc(r.full_name)+'">Remove</button></li>'}).join('')+'</ul>':'<p class="mc-empty">No repositories imported. Jarvis can read imported repositories (read-only).</p>'}
    catch(e){box.innerHTML='<p class="mc-empty">'+esc(e.message)+'</p>'}
  }
  async function importRepo(e){
    e.preventDefault();var owner=$('mcRepoOwner').value.trim(),repo=$('mcRepoName').value.trim();if(!owner||!repo)return;
    say('mcRepoStatus','Importing…');
    try{var d=await MC.post('/mission-control/repo-import/connect',{owner:owner,repo:repo});
      if(d.error)throw new Error(d.error);say('mcRepoStatus','Imported.');$('mcRepoOwner').value='';$('mcRepoName').value='';loadRepos()}
    catch(err){say('mcRepoStatus','Not imported: '+err.message,true)}
  }
  async function removeRepo(name){
    if(!window.confirm('Remove '+name+'? Jarvis will no longer read it.'))return;
    try{await MC.post('/mission-control/repo-import/remove',{full_name:name});loadRepos()}catch(e){say('mcRepoStatus',e.message,true)}
  }

  function load(){loadAi();loadEmail();loadCredentials();loadRepos()}
  MC.onShow=MC.onShow||{};MC.onShow.settings=load;
  $('mcAiProvider').addEventListener('change',function(){fillModels()});
  $('mcAiSave').addEventListener('click',function(){save('/mission-control/runtime/ai-provider',{provider:$('mcAiProvider').value,model:$('mcAiModel').value},'mcAiStatus',loadAi)});
  $('mcReviewSave').addEventListener('click',function(){save('/mission-control/runtime/independent-review',{enabled:$('mcReview').value==='on'},'mcReviewStatus',loadAi)});
  $('mcEmailSave').addEventListener('click',function(){save('/mission-control/runtime/smtp-provider',{provider:$('mcEmailProvider').value},'mcEmailStatus',loadEmail)});
  $('mcGithubCheck').addEventListener('click',checkGithub);
  $('mcRepoForm').addEventListener('submit',importRepo);
  $('mcCreds').addEventListener('click',credentialAction);
  $('mcCreds').addEventListener('submit',credentialSave);
  $('mcRepos').addEventListener('click',function(e){var b=e.target.closest('[data-remove-repo]');if(b)removeRepo(b.dataset.removeRepo)});
  $('mcLogout').addEventListener('click',async function(){try{await MC.post('/mission-control/auth/logout')}catch(e){}
    try{localStorage.removeItem('mission_control_token')}catch(e){}MC.toLogin()});
})();
"""
