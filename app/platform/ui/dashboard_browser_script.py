from __future__ import annotations

from app.platform.ui.login_module import render_login_script


def render_dashboard_browser_script() -> str:
    return r"""<script>(function(){
__LOGIN_SCRIPT__
var AI_PROVIDER_KEY='mission_control_ai_provider';
var AI_MODEL_KEY='mission_control_ai_model';
var GITHUB_LINKED_KEY='mission_control_github_linked';
var AI_PROVIDERS={
  openai:{label:'OpenAI',defaultModel:'gpt-5.5',models:['gpt-5.5','gpt-5.5-mini','gpt-5.5-thinking']},
  deepseek:{label:'DeepSeek',defaultModel:'deepseek-v4-pro',models:['deepseek-v4-pro','deepseek-v4-flash']}
};
function render(data){return typeof data==='string'?data:JSON.stringify(data,null,2)}
function showResult(id,data){var el=byId(id);if(el){el.textContent=render(data)}}
function scopeText(){return 'Create a concise Scope of Work from this Board Room discussion. Include: objective, in scope, out of scope, acceptance criteria, risks, founder approval needed, and Mission Runtime handoff summary. Discussion: '+byId('message').value}
function runtimeGoal(){return 'Preview Mission Runtime handoff for this approved Scope of Work: '+byId('message').value}
function validProvider(value){return AI_PROVIDERS[value]?value:'openai'}
function providerConfig(provider){return AI_PROVIDERS[validProvider(provider)]}
function providerDefault(provider){return providerConfig(provider).defaultModel}
function validModel(provider,model){return providerConfig(provider).models.indexOf(model)>=0}
function setAiSelection(provider,model){
  provider=validProvider(provider);
  if(!validModel(provider,model)){model=providerDefault(provider)}
  localStorage.setItem(AI_PROVIDER_KEY,provider);
  localStorage.setItem(AI_MODEL_KEY,model);
  return {provider:provider,model:model};
}
function aiSelection(){return setAiSelection(localStorage.getItem(AI_PROVIDER_KEY)||'openai',localStorage.getItem(AI_MODEL_KEY))}
function aiProvider(){return aiSelection().provider}
function aiModel(){return aiSelection().model}
function aiPayload(){var selected=aiSelection();return {provider:selected.provider,model:selected.model}}
function githubLinked(){return localStorage.getItem(GITHUB_LINKED_KEY)!=='false'}
function setGithubLinked(value){localStorage.setItem(GITHUB_LINKED_KEY,value?'true':'false')}
function setText(id,value){var el=byId(id);if(el){el.textContent=value}}
function setGithubRows(data){
  data=data||{};
  var credential=(data.credential_status&&data.credential_status.credential)||(data.credential&&data.credential)||{};
  var policy=(data.credential_status&&data.credential_status.repository_policy)||data.repository_policy||{};
  var readiness=(data.credential_status&&data.credential_status.readiness)||data.readiness||{};
  var checks=data.checks||data.github_checks||{};
  setText('githubRowStatus',data.status||'unknown');
  setText('githubRowRepository',data.repository||policy.default_repository||'unknown');
  setText('githubRowAuth',credential.status||((credential.token_present||readiness.github_connected)?'configured':'missing'));
  setText('githubRowRepoCheck',String(checks.repository_check||checks.repository||readiness.github_connected||false));
  setText('githubRowBranchesCheck',String(checks.branches_check||checks.branches||false));
  setText('githubRowPullRequestsCheck',String(checks.pull_requests_check||checks.pull_requests||checks.prs||false));
  setText('githubRowActionsCheck',String(checks.actions_check||checks.actions||false));
  setText('githubRowTokenVisible',String(Boolean(credential.token_value_exposed||data.token_value_exposed)));
}
function showSection(name){document.querySelectorAll('.section').forEach(function(s){s.classList.remove('active')});document.querySelectorAll('.nav button').forEach(function(b){b.classList.remove('active')});var section=byId(name);if(section){section.classList.add('active')}var nav=document.querySelector('.nav button[data-section="'+name+'"]');if(nav){nav.classList.add('active')}if(name==='settings'){syncGithubUi();if(githubLinked()){checkGithubHealth()}}}
async function sendBoardRoom(){showResult('result','Board Room is thinking...');try{showResult('result',await post('/mission-control/operating-console/chat',Object.assign({token:token,message:byId('message').value},aiPayload())))}catch(e){showResult('result','Board Room request failed: '+e)}}
async function createProposal(){showResult('proposalResult','Creating scope of work...');try{showResult('proposalResult',await post('/mission-control/operating-console/workflow',Object.assign({token:token,action:'create-scope-of-work',message:scopeText()},aiPayload())))}catch(e){showResult('proposalResult','Scope request failed: '+e)}}
async function runRuntime(){showResult('proposalResult','Running Mission Runtime handoff preview...');try{showResult('proposalResult',await post('/platform/mission-runtime/run',Object.assign({token:token,goal:runtimeGoal()},aiPayload())))}catch(e){showResult('proposalResult','Runtime request failed: '+e)}}
function refreshModelOptions(provider,selectedModel){
  var modelSelect=byId('aiModelInput');
  if(!modelSelect)return;
  provider=validProvider(provider);
  var models=providerConfig(provider).models;
  modelSelect.innerHTML='';
  models.forEach(function(model){var option=document.createElement('option');option.value=model;option.textContent=model;modelSelect.appendChild(option)});
  modelSelect.value=validModel(provider,selectedModel)?selectedModel:providerDefault(provider);
}
function refreshAiProviderStatus(){
  var selected=aiSelection();
  var providerSelect=byId('aiProviderSelect');
  if(providerSelect){providerSelect.value=selected.provider}
  refreshModelOptions(selected.provider,selected.model);
  var providerStatus=byId('aiProviderStatus');
  if(providerStatus){providerStatus.textContent='Selected AI: '+providerConfig(selected.provider).label+' - '+selected.model}
}
function saveAiFromControls(){
  var providerSelect=byId('aiProviderSelect');
  var modelSelect=byId('aiModelInput');
  var selected=setAiSelection(providerSelect?providerSelect.value:aiProvider(),modelSelect?modelSelect.value:aiModel());
  refreshAiProviderStatus();
  return selected;
}
function syncGithubUi(){
  var linked=githubLinked();
  var btn=byId('githubLinkBtn');
  if(btn){btn.textContent=linked?'Unlink GitHub':'Link GitHub'}
  var healthBtn=byId('githubHealthBtn');
  if(healthBtn){healthBtn.disabled=!linked}
  if(!linked){
    setText('githubHealth','GitHub unlinked');
    setText('githubRowStatus','GitHub unlinked');
    setText('githubRowRepository','-');
    setText('githubRowAuth','-');
    setText('githubRowRepoCheck','-');
    setText('githubRowBranchesCheck','-');
    setText('githubRowPullRequestsCheck','-');
    setText('githubRowActionsCheck','-');
    setText('githubRowTokenVisible','false');
    showResult('githubHealthResult','GitHub unlinked');
  }
}
async function checkGithubHealth(){
  if(!githubLinked()){syncGithubUi();return}
  showResult('githubHealthResult','Checking GitHub connection...');
  try{
    var data=await post('/mission-control/github/health',{token:token});
    setText('githubHealth',data.status||'unknown');
    setGithubRows(data);
    showResult('githubHealthResult',data);
  }catch(e){
    setText('githubHealth','GitHub health check failed');
    showResult('githubHealthResult','GitHub health check failed: '+e);
  }
}
document.addEventListener('DOMContentLoaded',function(){
  bindLoginModule();
  byId('openBoardBtn').addEventListener('click',function(){showSection('board')});
  byId('boardBtn').addEventListener('click',sendBoardRoom);
  byId('proposalBtn').addEventListener('click',createProposal);
  byId('runtimeBtn').addEventListener('click',runRuntime);
  byId('clearBoardBtn').addEventListener('click',function(){byId('message').value='';showResult('result','Ready.');showResult('proposalResult','No scope of work created yet.')});
  document.querySelectorAll('.nav button[data-section]').forEach(function(b){b.addEventListener('click',function(){showSection(this.dataset.section)})});
  document.querySelectorAll('button[data-jump]').forEach(function(b){b.addEventListener('click',function(){showSection(this.dataset.jump)})});
  document.querySelectorAll('button[data-template]').forEach(function(b){b.addEventListener('click',function(){byId('message').value=this.dataset.template;showSection('board')})});
  refreshAiProviderStatus();
  if(byId('aiProviderSelect')){byId('aiProviderSelect').addEventListener('change',function(){var selected=setAiSelection(this.value,null);refreshModelOptions(selected.provider,selected.model);refreshAiProviderStatus()})}
  if(byId('aiModelInput')){byId('aiModelInput').addEventListener('change',saveAiFromControls)}
  if(byId('saveAiProviderBtn')){byId('saveAiProviderBtn').addEventListener('click',saveAiFromControls)}
  if(byId('githubHealthBtn')){byId('githubHealthBtn').addEventListener('click',checkGithubHealth)}
  if(byId('githubLinkBtn')){byId('githubLinkBtn').addEventListener('click',function(){var next=!githubLinked();setGithubLinked(next);syncGithubUi();if(next){checkGithubHealth()}})}
  if(byId('githubDetailsToggle')){byId('githubDetailsToggle').addEventListener('click',function(){var panel=byId('githubHealthResult');if(!panel)return;var hidden=panel.style.display==='none';panel.style.display=hidden?'block':'none';this.textContent=hidden?'Hide Technical Details':'Show Technical Details'})}
  setGithubLinked(githubLinked());
  syncGithubUi();
  if(githubLinked()){checkGithubHealth()}
})();
})();</script>""".replace(
        "__LOGIN_SCRIPT__",
        render_login_script(),
    )
