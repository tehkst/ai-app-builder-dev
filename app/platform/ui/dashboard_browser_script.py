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
function executiveText(data){if(!data||typeof data!=='object'||!window.ExecutivePresenter||!(data.mission||data.active_mission))return render(data);
  var presented=window.ExecutivePresenter.presentMission(data);
  return ['Mission Created Successfully','','Mission: '+presented.title,'ID: '+presented.mission_id,'Status: '+presented.status,'','Executive Summary:',presented.executive_summary,'','Recommended Next Action:',presented.next_action,'','Technical details are available in the Mission Execution view.'].join('\n');
}
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
function friendlyStatus(value){
  if(value===true)return 'OK';
  if(value===false)return 'Needs attention';
  if(value&&typeof value==='object'){
    if(value.ok===true)return 'OK';
    if(value.ok===false)return value.status_code?('Needs attention ('+value.status_code+')'):'Needs attention';
    if(value.status)return friendlyStatus(value.status);
    return 'Not checked';
  }
  var text=String(value||'').replace(/_/g,'-');
  if(!text)return 'Not checked';
  if(text==='github-connected'||text==='ready'||text==='configured')return 'Connected';
  if(text==='github-partial')return 'Partially connected';
  if(text==='github-missing-token'||text==='missing'||text==='not_ready')return 'Needs token';
  if(text==='unauthorized')return 'Login required';
  return text.split('-').map(function(part){return part.charAt(0).toUpperCase()+part.slice(1)}).join(' ');
}
function checkValue(checks,name){
  return checks[name+'_check']||checks[name]||checks[name.replace('_','-')];
}
function setGithubRows(data){
  data=data||{};
  var credential=(data.credential_status&&data.credential_status.credential)||(data.credential&&data.credential)||{};
  var policy=(data.credential_status&&data.credential_status.repository_policy)||data.repository_policy||{};
  var readiness=(data.credential_status&&data.credential_status.readiness)||data.readiness||{};
  var checks=data.checks||data.github_checks||{};
  var tokenMounted=Boolean(data.token_mounted||credential.token_mounted||credential.token_present||readiness.github_connected);
  setText('githubRowRepository',data.repository||policy.default_repository||'unknown');
  setText('githubRowAuth',tokenMounted?'Secret mounted':'Token missing');
  setText('githubRowRepoCheck',friendlyStatus(checkValue(checks,'repository')||readiness.github_connected));
  setText('githubRowBranchesCheck',friendlyStatus(checkValue(checks,'branches')));
  setText('githubRowPullRequestsCheck',friendlyStatus(checkValue(checks,'pull_requests')||checks.prs));
  setText('githubRowActionsCheck',friendlyStatus(checkValue(checks,'actions')));
  setText('githubRowTokenVisible',String(Boolean(credential.token_value_exposed||data.token_value_exposed)));
}
function sectionFromLocation(){var name=String(window.location.hash||'').replace(/^#/,'');if(name==='agents')name='organisation';return document.querySelector('.nav button[data-section="'+name+'"]')?name:'home'} function showSection(name,updateUrl){if(name==='agents')name='organisation';document.querySelectorAll('.section').forEach(function(s){s.classList.remove('active')});document.querySelectorAll('.nav button').forEach(function(b){b.classList.remove('active')});var section=byId(name);if(!section){name='home';section=byId(name)}if(section){section.classList.add('active')}var nav=document.querySelector('.nav button[data-section="'+name+'"]');if(nav){nav.classList.add('active')}if(updateUrl!==false&&window.location.hash!=='#'+name){window.history.replaceState(null,'','#'+name)}if(name==='settings'){syncGithubUi();if(githubLinked()){checkGithubHealth()}}}
window.showSection=showSection;
async function sendBoardRoom(){showResult('result','Board Room is thinking...');try{var data=await post('/mission-control/operating-console/chat',Object.assign({token:token,message:byId('message').value},aiPayload()));showResult('result',data.board_room_response||data.message||'Board Room response received.')}catch(e){showResult('result','Board Room request failed: '+e)}}
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
  if(window.refreshBoardAiEngine){window.refreshBoardAiEngine()}
}
function saveAiFromControls(){
  var providerSelect=byId('aiProviderSelect');
  var modelSelect=byId('aiModelInput');
  var selected=setAiSelection(providerSelect?providerSelect.value:aiProvider(),modelSelect?modelSelect.value:aiModel());
  refreshAiProviderStatus();
  var saveBtn=byId('saveAiProviderBtn');
  if(saveBtn){
    saveBtn.textContent='Saved ✓';
    setTimeout(function(){saveBtn.textContent='Save AI Provider'},1600);
  }
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
    setText('githubHealth',friendlyStatus(data.status||data.connected));
    setGithubRows(data);
    showResult('githubHealthResult',data);
  }catch(e){
    setText('githubHealth','GitHub health check failed');
    showResult('githubHealthResult','GitHub health check failed: '+e);
  }
}

function executionFeedback(message,failed){var el=byId('executionMissionFeedback');if(!el)return;el.textContent=message||'';el.className=failed?'error':'good';el.style.display=message?'block':'none'} function syncExecutionAction(mission){var button=byId('advanceExecutionMissionBtn');if(!button)return;var action=mission&&mission.next_governed_action||{};button.textContent=action.label||'Continue Mission';button.dataset.actionType=action.action_type||'none';button.dataset.target=action.target||'';button.disabled=!mission||action.action_type==='none'||action.action_type==='founder_acceptance'||(action.action_type==='advance'&&!mission.advance_allowed)} function renderExecutionMission(data){var box=byId('executionMissionDashboard');if(!box)return;var mission=data.active_mission||data.mission;if(!mission){window.currentDurableMission=null;syncExecutionAction(null);box.innerHTML='<p class="muted">'+(data.message||'No active durable mission.')+'</p>';renderWorkflowMission(data);return}window.currentDurableMission=mission;syncExecutionAction(mission);if(window.ExecutivePresenter){box.innerHTML=window.ExecutivePresenter.missionCardHtml({mission:mission},data)}else{var stages=mission.stages||[];var rows=stages.map(function(st){return '<div class="row"><span>'+st.label+'</span><span class="'+(st.completed?'good':'muted')+'">'+(st.completed?'✓ Done':friendlyStatus(st.status||'Pending'))+'</span></div>'}).join('');box.innerHTML='<div class="row"><span>Mission</span><span>'+mission.title+'</span></div><div class="row"><span>Mission ID</span><span>'+mission.mission_id+'</span></div><div class="row"><span>Workflow Run ID</span><span>'+mission.workflow_run_id+'</span></div><div class="row"><span>Current Stage</span><span class="tag">'+mission.current_stage+'</span></div><h3>Timeline</h3>'+rows+'<p class="muted">'+(mission.blocker||mission.next_recommended_action||'Awaiting durable runtime progress.')+'</p>'}renderFounderAcceptance(box,mission);renderWorkflowMission(data)}
function renderWorkflowMission(data){var box=byId('workflowPipelineState');if(!box&&byId('workflows')){box=document.createElement('div');box.id='workflowPipelineState';box.className='card';byId('workflows').appendChild(box)}if(!box)return;var mission=data&&data.active_mission;if(!mission){box.innerHTML='<p class="muted">No durable workflow mission is active.</p>';return}var task=mission.task_status&&mission.task_status.current;box.innerHTML='<div class="row"><span>Mission</span><span>'+mission.title+'</span></div><div class="row"><span>Mission ID</span><span>'+mission.mission_id+'</span></div><div class="row"><span>Workflow Run</span><span>'+mission.workflow_run_id+'</span></div><div class="row"><span>Current Stage</span><span>'+mission.current_stage+'</span></div><div class="row"><span>Progress</span><span>'+(mission.progress_percentage===null?'Unknown':mission.progress_percentage+'%')+'</span></div><div class="row"><span>Worker Task</span><span>'+(task?(task.task_id+' · '+friendlyStatus(task.status)):'No task')+'</span></div>'+(mission.blocker?'<div class="row"><span>Blocker</span><span>'+mission.blocker+'</span></div>':'')}
async function refreshExecutionMission(){try{var response=await fetch('/mission-control/execution');var data=await response.json();renderExecutionMission(data);showResult('executionMissionResult',data)}catch(e){showResult('executionMissionResult','Execution refresh failed: '+e)}}
async function createExecutionMission(){var action=window.currentDurableMissionAction;if(!action||!action.payload){var message='Select or create a Board Room mission before creating an execution mission.';showResult('executionMissionResult',message);renderExecutionMission({message:message,active_mission:null});return}showResult('executionMissionResult','Creating durable execution mission...');try{var data=await post('/mission-control/operating-console/action',Object.assign({token:token},action.payload));if(!data.workflow_run_id)throw new Error(data.message||'Mission Control did not return a durable workflow run.');if(window.acceptDurableMissionResult)window.acceptDurableMissionResult(data);renderExecutionMission({active_mission:data});showResult('executionMissionResult',data);showSection('execution')}catch(e){showResult('executionMissionResult','Execution mission creation failed: '+e)}}
async function advanceExecutionMission(){var mission=window.currentDurableMission;if(!mission||!mission.workflow_run_id){executionFeedback('Load a durable mission before continuing it.',true);return}executionFeedback('Continuing durable mission...',false);try{var data=await post('/mission-control/execution/advance',{token:token,mission_id:mission.mission_id,workflow_run_id:mission.workflow_run_id});if(data.ok===false||data.status==='failed'||data.status==='blocked'){throw new Error(data.message||(data.error&&data.error.technical_summary)||'Mission continuation failed.')}if(window.acceptDurableMissionResult)window.acceptDurableMissionResult(data);executionFeedback(data.message||'Mission continuation requested.',false);await refreshExecutionMission()}catch(e){executionFeedback('Execution continuation failed: '+(e.message||e),true)}} function runExecutionNextAction(){var button=byId('advanceExecutionMissionBtn'),type=button&&button.dataset.actionType,target=button&&button.dataset.target;if(type==='advance'){advanceExecutionMission();return}if(type==='show_section'&&target){showSection(target);return}executionFeedback('No safe next action is available for this mission state.',true)}
function missionLink(){var mission=window.currentDurableMission||{};return {mission_id:mission.mission_id||'',workflow_run_id:mission.workflow_run_id||'',execution_metadata:{mission_id:mission.mission_id||''}}} function renderFounderAcceptance(box,mission){if(!box||!mission||mission.current_stage!=='founder_acceptance')return;var panel=document.createElement('div');panel.className='card';panel.innerHTML='<h3>Founder Acceptance</h3><p class="muted">Production verification passed. Choose the release outcome.</p><div class="actions"><button data-acceptance="accept_release">Accept Release</button><button data-acceptance="request_fix">Request Fix</button><button data-acceptance="request_rollback">Roll Back</button><button data-acceptance="defer_acceptance">Defer Acceptance</button></div>';box.appendChild(panel);panel.querySelectorAll('button[data-acceptance]').forEach(function(button){button.addEventListener('click',function(){submitFounderAcceptance(this.dataset.acceptance)})})} async function submitFounderAcceptance(action){var mission=window.currentDurableMission;if(!mission)return;var actionId=mission.workflow_run_id+':'+action;try{var data=await post('/mission-control/execution/acceptance',{token:token,mission_id:mission.mission_id,workflow_run_id:mission.workflow_run_id,action:action,action_id:actionId});if(data.ok===false)throw new Error(data.message||'Founder acceptance failed.');renderExecutionMission({active_mission:data});executionFeedback(data.message||'Release decision recorded.',false)}catch(e){executionFeedback('Release decision failed: '+(e.message||e),true)}}

function installBoardRoomMissionButton(){var anchor=byId('proposalBtn');if(!anchor||byId('createExecutionFromBoardBtn'))return;var btn=document.createElement('button');btn.id='createExecutionFromBoardBtn';btn.className='primary';btn.textContent='Create Execution Mission';btn.addEventListener('click',createMissionFromBoardRoom);anchor.parentElement.appendChild(btn)}
async function createMissionFromBoardRoom(){await createExecutionMission()}
function installBoardRoomPlannerButton(){var anchor=byId('proposalBtn');if(!anchor||byId('generateEngineeringPlanBtn'))return;var btn=document.createElement('button');btn.id='generateEngineeringPlanBtn';btn.className='secondary';btn.textContent='Generate Engineering Plan';btn.addEventListener('click',generateEngineeringPlanFromBoardRoom);anchor.parentElement.appendChild(btn)}
async function generateEngineeringPlanFromBoardRoom(){var msg=byId('message')?byId('message').value:'';if(!msg){msg=byId('result')?byId('result').textContent:''}showResult('proposalResult','Generating engineering plan...');try{var data=await post('/mission-control/planning/generate',Object.assign({token:token,message:msg},aiPayload()));showResult('proposalResult',data)}catch(e){showResult('proposalResult','Engineering plan failed: '+e)}}
function installEngineeringBreakdownButton(){var anchor=byId('proposalBtn');if(!anchor||byId('generateEngineeringBreakdownBtn'))return;var btn=document.createElement('button');btn.id='generateEngineeringBreakdownBtn';btn.className='secondary';btn.textContent='Generate Engineering Breakdown';btn.addEventListener('click',generateEngineeringBreakdownFromBoardRoom);anchor.parentElement.appendChild(btn)}
async function generateEngineeringBreakdownFromBoardRoom(){var msg=byId('message')?byId('message').value:'';var raw=byId('proposalResult')?byId('proposalResult').textContent:'';var planner=null;try{planner=raw&&raw.trim().charAt(0)==='{'?JSON.parse(raw):null}catch(e){planner=null}if(!msg){msg=byId('result')?byId('result').textContent:''}showResult('proposalResult','Generating engineering breakdown...');try{var data=await post('/mission-control/engineering-manager/breakdown',{token:token,founder_request:msg,planner_output:planner});showResult('proposalResult',data)}catch(e){showResult('proposalResult','Engineering breakdown failed: '+e)}}
function installGithubExecutionPanel(){var section=byId('executions');if(!section||byId('githubExecutionJson'))return;var card=document.createElement('div');card.className='card';card.innerHTML='<h2>GitHub Execution</h2><p class="muted">Founder-approved feature branch, commit, push, and PR creation only.</p><textarea id="githubExecutionJson" style="min-height:220px">{\n  "mission_id": "MC-GH-EXEC-01",\n  "title": "Approved GitHub execution",\n  "branch_name": "codex/approved-github-execution",\n  "commit_message": "Implement approved GitHub execution",\n  "pr_title": "Implement approved GitHub execution",\n  "pr_body": "Founder-approved GitHub execution payload.",\n  "file_changes": [],\n  "live_execution": false,\n  "approval_phrase": ""\n}</textarea><div class="actions"><button class="secondary" id="githubExecutionLoadBtn">Load Verified Changes</button><button class="secondary" id="githubExecutionPreviewBtn">Preview</button><button class="primary" id="githubExecutionExecuteBtn">Execute with approval phrase</button></div><pre id="githubExecutionResult">No GitHub execution preview yet.</pre>';section.appendChild(card);var pr=document.createElement('div');pr.className='card';pr.innerHTML='<h2>PR Lifecycle</h2><label>PR number</label><input id="githubPrNumberInput" inputmode="numeric" placeholder="353"><div class="actions"><button class="secondary" id="githubPrStatusBtn">Check PR Status</button></div><pre id="githubPrResult">No PR checked yet.</pre>';section.appendChild(pr);byId('githubExecutionLoadBtn').addEventListener('click',loadVerifiedGithubChanges);byId('githubExecutionPreviewBtn').addEventListener('click',previewGithubExecution);byId('githubExecutionExecuteBtn').addEventListener('click',executeGithubExecution);byId('githubPrStatusBtn').addEventListener('click',checkGithubPrLifecycle)}
function githubExecutionPayload(){var raw=byId('githubExecutionJson')?byId('githubExecutionJson').value:'{}';var payload=JSON.parse(raw);var link=missionLink();payload.token=token;if(link.mission_id)payload.mission_id=link.mission_id;if(link.workflow_run_id)payload.workflow_run_id=link.workflow_run_id;return payload} async function loadVerifiedGithubChanges(){var link=missionLink();if(!link.mission_id||!link.workflow_run_id){showResult('githubExecutionResult','Load a durable mission first.');return}try{var data=await post('/mission-control/execution/repository-package',{token:token,mission_id:link.mission_id,workflow_run_id:link.workflow_run_id});if(data.ok===false)throw new Error(data.message||'Verified changes are unavailable.');var source=data.repository_execution||{},execution=source.execution||{};byId('githubExecutionJson').value=JSON.stringify({mission_id:link.mission_id,workflow_run_id:link.workflow_run_id,title:execution.title||'Verified mission changes',branch_name:execution.feature_branch,commit_message:execution.commit_message,pr_title:execution.pr_title,pr_body:execution.pr_body,file_changes:execution.write_batch||[],live_execution:false,approval_phrase:''},null,2);showResult('githubExecutionResult','Verified changes loaded. Preview them before approval.')}catch(e){showResult('githubExecutionResult','Verified changes could not be loaded: '+(e.message||e))}}
async function previewGithubExecution(){showResult('githubExecutionResult','Previewing approved GitHub execution...');try{showResult('githubExecutionResult',await post('/mission-control/github-execution/preview',githubExecutionPayload()))}catch(e){showResult('githubExecutionResult','GitHub execution preview failed: '+e)}}
async function executeGithubExecution(){showResult('githubExecutionResult','Running approved GitHub execution...');try{showResult('githubExecutionResult',await post('/mission-control/github-execution/execute',githubExecutionPayload()))}catch(e){showResult('githubExecutionResult','GitHub execution failed: '+e)}}
function renderPrLifecycle(data){if(!data||data.status==='blocked')return render(data);var s=data.checks_summary||{};return ['Status: '+data.status,'Repository: '+data.repository,'PR: #'+data.pr_number+' '+(data.title||''),'URL: '+(data.pr_url||'-'),'State: '+data.state,'Merged: '+String(data.merged),'Mergeable: '+String(data.mergeable),'Branches: '+data.head_branch+' -> '+data.base_branch,'Changed files: '+data.changed_files+' (+'+data.additions+' / -'+data.deletions+')','Checks: '+(s.overall||'unknown')+' ('+(s.passing||0)+' passing, '+(s.failing||0)+' failing, '+(s.pending||0)+' pending)','Next: '+data.recommended_action,'Founder approval required: '+String(data.founder_approval_required)].join('\n')}
async function checkGithubPrLifecycle(){showResult('githubPrResult','Checking PR status...');try{var data=await post('/mission-control/github-pr/status',Object.assign({token:token,pr_number:byId('githubPrNumberInput').value},missionLink()));showResult('githubPrResult',renderPrLifecycle(data))}catch(e){showResult('githubPrResult','PR status check failed: '+e)}}
function installGithubMergePanel(){var section=byId('executions');if(!section||byId('githubMergePrNumberInput'))return;var card=document.createElement('div');card.className='card';card.innerHTML='<h2>Founder-approved PR Merge</h2><label>PR number</label><input id="githubMergePrNumberInput" inputmode="numeric" placeholder="353"><label>Merge method</label><select id="githubMergeMethodInput"><option value="squash">squash</option><option value="merge">merge</option><option value="rebase">rebase</option></select><label>Approval phrase</label><input id="githubMergeApprovalInput" placeholder="I APPROVE PR MERGE"><div class="actions"><button class="secondary" id="githubMergePreviewBtn">Preview Merge</button><button class="primary" id="githubMergeExecuteBtn">Execute Merge</button></div><pre id="githubMergeResult">No merge preview yet.</pre>';section.appendChild(card);byId('githubMergePreviewBtn').addEventListener('click',previewGithubMerge);byId('githubMergeExecuteBtn').addEventListener('click',executeGithubMerge)}
function githubMergePayload(live){return Object.assign({token:token,pr_number:byId('githubMergePrNumberInput').value,merge_method:byId('githubMergeMethodInput').value,approval_phrase:byId('githubMergeApprovalInput').value,live_execution:live},missionLink())}
async function previewGithubMerge(){showResult('githubMergeResult','Previewing merge...');try{showResult('githubMergeResult',await post('/mission-control/github-merge/preview',githubMergePayload(false)))}catch(e){showResult('githubMergeResult','Merge preview failed: '+e)}}
async function executeGithubMerge(){showResult('githubMergeResult','Executing founder-approved merge...');try{showResult('githubMergeResult',await post('/mission-control/github-merge/execute',githubMergePayload(true)))}catch(e){showResult('githubMergeResult','Merge failed: '+e)}}
function installCloudRunDeployPanel(){var section=byId('executions');if(!section||byId('cloudRunDeployApprovalInput'))return;var card=document.createElement('div');card.className='card';card.innerHTML='<h2>Founder-approved Cloud Run Deployment</h2><label>Approval phrase</label><input id="cloudRunDeployApprovalInput" placeholder="I APPROVE CLOUD RUN DEPLOYMENT"><div class="actions"><button class="secondary" id="cloudRunDeployPreviewBtn">Preview Deploy</button><button class="primary" id="cloudRunDeployExecuteBtn">Execute Deploy</button></div><pre id="cloudRunDeployResult">No deployment preview yet.</pre>';section.appendChild(card);byId('cloudRunDeployPreviewBtn').addEventListener('click',previewCloudRunDeploy);byId('cloudRunDeployExecuteBtn').addEventListener('click',executeCloudRunDeploy)}
function cloudRunDeployPayload(live){return Object.assign({token:token,service_name:'ai-software-factory-production',region:'asia-southeast1',project_id:'ai-software-factory-500910',source_ref:'main',approval_phrase:byId('cloudRunDeployApprovalInput').value,live_execution:live},missionLink())}
async function previewCloudRunDeploy(){showResult('cloudRunDeployResult','Previewing deployment...');try{showResult('cloudRunDeployResult',await post('/mission-control/deployment/preview',cloudRunDeployPayload(false)))}catch(e){showResult('cloudRunDeployResult','Deployment preview failed: '+e)}}
async function executeCloudRunDeploy(){showResult('cloudRunDeployResult','Executing founder-approved deployment...');try{showResult('cloudRunDeployResult',await post('/mission-control/deployment/execute',cloudRunDeployPayload(true)))}catch(e){showResult('cloudRunDeployResult','Deployment failed: '+e)}}
function installProductionVerificationPanel(){var section=byId('executions');if(!section||byId('productionVerifyUrlInput'))return;var card=document.createElement('div');card.className='card';card.innerHTML='<h2>Automated Production Verification</h2><label>Service URL</label><input id="productionVerifyUrlInput" value="https://ai-software-factory-production-85787156520.asia-southeast1.run.app"><div class="actions"><button class="secondary" id="productionVerifyBtn">Run Verification</button></div><pre id="productionVerifyResult">No production verification yet.</pre>';section.appendChild(card);byId('productionVerifyBtn').addEventListener('click',runProductionVerification)}
async function runProductionVerification(){showResult('productionVerifyResult','Running production verification...');try{showResult('productionVerifyResult',await post('/mission-control/verification/run',Object.assign({token:token,service_url:byId('productionVerifyUrlInput').value,service_name:'ai-software-factory-production',region:'asia-southeast1',project_id:'ai-software-factory-500910'},missionLink())))}catch(e){showResult('productionVerifyResult','Production verification failed: '+e)}}
function installCloudRunRollbackPanel(){var section=byId('executions');if(!section||byId('cloudRunRollbackTargetInput'))return;var card=document.createElement('div');card.className='card';card.innerHTML='<h2>Founder-approved Rollback</h2><label>Target revision</label><input id="cloudRunRollbackTargetInput" placeholder="ai-software-factory-production-xxxxx"><label>Approval phrase</label><input id="cloudRunRollbackApprovalInput" placeholder="I APPROVE CLOUD RUN ROLLBACK"><div class="actions"><button class="secondary" id="cloudRunRollbackPreviewBtn">Preview Rollback</button><button class="primary" id="cloudRunRollbackExecuteBtn">Execute Rollback</button></div><pre id="cloudRunRollbackResult">No rollback preview yet.</pre>';section.appendChild(card);byId('cloudRunRollbackPreviewBtn').addEventListener('click',previewCloudRunRollback);byId('cloudRunRollbackExecuteBtn').addEventListener('click',executeCloudRunRollback)}
function cloudRunRollbackPayload(live){return {token:token,service_name:'ai-software-factory-production',region:'asia-southeast1',project_id:'ai-software-factory-500910',target_revision:byId('cloudRunRollbackTargetInput').value,approval_phrase:byId('cloudRunRollbackApprovalInput').value,live_execution:live}}
async function previewCloudRunRollback(){showResult('cloudRunRollbackResult','Previewing rollback...');try{showResult('cloudRunRollbackResult',await post('/mission-control/rollback/preview',cloudRunRollbackPayload(false)))}catch(e){showResult('cloudRunRollbackResult','Rollback preview failed: '+e)}}
async function executeCloudRunRollback(){showResult('cloudRunRollbackResult','Executing founder-approved rollback...');try{showResult('cloudRunRollbackResult',await post('/mission-control/rollback/execute',cloudRunRollbackPayload(true)))}catch(e){showResult('cloudRunRollbackResult','Rollback failed: '+e)}}
document.addEventListener('DOMContentLoaded',function(){
  bindLoginModule();installBoardRoomPlannerButton();installEngineeringBreakdownButton();installBoardRoomMissionButton();installGithubExecutionPanel();installGithubMergePanel();installCloudRunDeployPanel();installProductionVerificationPanel();installCloudRunRollbackPanel();if(byId('createExecutionMissionBtn')){byId('createExecutionMissionBtn').addEventListener('click',createExecutionMission)}if(byId('advanceExecutionMissionBtn')){byId('advanceExecutionMissionBtn').addEventListener('click',runExecutionNextAction)}if(byId('refreshExecutionMissionBtn')){byId('refreshExecutionMissionBtn').addEventListener('click',refreshExecutionMission)}showSection(sectionFromLocation(),false);window.addEventListener('hashchange',function(){showSection(sectionFromLocation(),false)});refreshExecutionMission();
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
  syncGithubUi();if(window.refreshExecutiveState)window.refreshExecutiveState();if(window.refreshBusinessMetrics)window.refreshBusinessMetrics();
  if(githubLinked()){checkGithubHealth()}
})();
})();</script>""".replace(
        "__LOGIN_SCRIPT__",
        render_login_script(),
    )
