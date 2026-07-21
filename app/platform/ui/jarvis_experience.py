from __future__ import annotations


JARVIS_STYLE = r"""
<style>
.br-composer{grid-template-columns:auto minmax(0,1fr) auto;align-items:end}
.jarvis-attach-button{width:46px;height:46px;border:1px solid #2b4167;border-radius:15px;background:#0b192d;color:#dbeafe;font-size:22px;font-weight:800;display:grid;place-items:center}
.jarvis-attach-button:hover{background:#132541;border-color:#4f6f9f}
.jarvis-attachments{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px;padding:0 2px}
.jarvis-attachment{display:flex;align-items:center;gap:8px;max-width:320px;border:1px solid #2c4268;background:#0b1729;border-radius:12px;padding:8px 10px;color:#dbeafe}
.jarvis-attachment-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;font-weight:750}
.jarvis-attachment-meta{font-size:10px;color:#8ea5c8}
.jarvis-attachment-remove{border:0;background:transparent;color:#9fb4d8;padding:0;font-size:16px}
.jarvis-drop-active{outline:2px dashed #60a5fa;outline-offset:-8px;background:#0a1930!important}
.jarvis-attachment-error{grid-column:1/-1;color:#fda4af;font-size:12px;min-height:16px}
</style>
"""


JARVIS_SCRIPT = r"""
<script>
(function(){
  var MAX_FILES=5, MAX_FILE_BYTES=1024*1024, MAX_TOTAL_BYTES=3*1024*1024;
  var pendingAttachments=[];
  var SESSION_KEY='br_ui_sessions_v2', ACTIVE_KEY='br_ui_active_session_id', DRAFT_KEY='jarvis_active_draft_v1', TAB_KEY='jarvis_tab_session_v1';
  var TEXT_EXTENSIONS=['txt','md','markdown','json','csv','tsv','xml','yaml','yml','toml','ini','cfg','conf','log','py','js','jsx','ts','tsx','css','scss','html','htm','sql','sh','bash','zsh','java','go','rs','rb','php','c','h','cpp','hpp','cs','kt','swift'];
  if(!sessionStorage.getItem(TAB_KEY)){localStorage.removeItem(ACTIVE_KEY);sessionStorage.setItem(TAB_KEY,'active')}
  function byId(id){return document.getElementById(id)}
  function fileExtension(name){var parts=String(name||'').toLowerCase().split('.');return parts.length>1?parts.pop():''}
  function isReadableText(file){return String(file.type||'').indexOf('text/')===0||TEXT_EXTENSIONS.indexOf(fileExtension(file.name))>=0||['application/json','application/xml','application/javascript'].indexOf(file.type)>=0}
  function sizeLabel(bytes){if(bytes<1024)return bytes+' B';if(bytes<1024*1024)return (bytes/1024).toFixed(1)+' KB';return (bytes/(1024*1024)).toFixed(1)+' MB'}
  function setError(text){var node=byId('jarvisAttachmentError');if(node)node.textContent=text||''}
  function readFile(file){return new Promise(function(resolve,reject){var reader=new FileReader();reader.onerror=function(){reject(new Error('Could not read '+file.name))};reader.onload=function(){resolve(String(reader.result||''))};if(isReadableText(file))reader.readAsText(file);else reader.readAsDataURL(file)})}
  function attachmentSummary(item){return {name:item.name,size:item.size,mime_type:item.mime_type,kind:item.kind,content:item.content}}
  function readSessions(){try{return JSON.parse(localStorage.getItem(SESSION_KEY)||'[]')}catch(e){return []}}
  function writeSessions(items){localStorage.setItem(SESSION_KEY,JSON.stringify(items.slice(0,30)))}
  function markActiveState(state){var id=localStorage.getItem(ACTIVE_KEY);if(!id)return;var items=readSessions(), changed=false;items.forEach(function(item){if(item.id===id){item.lifecycle_state=state;item.updated_at=new Date().toISOString();changed=true}});if(changed)writeSessions(items)}
  function archiveActiveSession(){var id=localStorage.getItem(ACTIVE_KEY);if(!id)return;var items=readSessions(), keep=false;items.forEach(function(item){if(item.id===id){var hasFounder=(item.messages||[]).some(function(message){return message.role==='user'});if(hasFounder){item.lifecycle_state='archived';item.archived_at=new Date().toISOString();item.updated_at=item.archived_at;keep=true}}});if(keep)writeSessions(items);localStorage.removeItem(ACTIVE_KEY)}
  function clearDraft(){localStorage.removeItem(DRAFT_KEY)}
  function restoreDraft(){var input=byId('message');if(input&&!input.value){input.value=localStorage.getItem(DRAFT_KEY)||''}}
  function renderAttachments(){var row=byId('jarvisAttachments');if(!row)return;row.innerHTML='';pendingAttachments.forEach(function(item,index){var chip=document.createElement('div');chip.className='jarvis-attachment';chip.innerHTML='<div style="min-width:0"><div class="jarvis-attachment-name"></div><div class="jarvis-attachment-meta"></div></div><button class="jarvis-attachment-remove" type="button" aria-label="Remove attachment">×</button>';chip.querySelector('.jarvis-attachment-name').textContent=item.name;chip.querySelector('.jarvis-attachment-meta').textContent=(item.kind==='text'?'Readable text':'Binary file')+' · '+sizeLabel(item.size);chip.querySelector('button').onclick=function(){pendingAttachments.splice(index,1);renderAttachments()};row.appendChild(chip)})}
  async function addFiles(fileList){setError('');var files=Array.prototype.slice.call(fileList||[]);if(!files.length)return;if(pendingAttachments.length+files.length>MAX_FILES){setError('Jarvis accepts up to '+MAX_FILES+' attachments per message.');return}var currentBytes=pendingAttachments.reduce(function(total,item){return total+item.size},0);for(var i=0;i<files.length;i++){var file=files[i];if(file.size>MAX_FILE_BYTES){setError(file.name+' is larger than 1 MB.');continue}if(currentBytes+file.size>MAX_TOTAL_BYTES){setError('The combined attachment limit is 3 MB.');break}try{var content=await readFile(file);pendingAttachments.push({name:file.name,size:file.size,mime_type:file.type||'application/octet-stream',kind:isReadableText(file)?'text':'binary',content:content});currentBytes+=file.size}catch(error){setError(error.message||'An attachment could not be read.')}}renderAttachments()}
  function meaningfulActionCard(card){if(!card)return false;var labels=Array.from(card.querySelectorAll('.br-actions button')).map(function(button){return String(button.textContent||'').trim().toLowerCase()});if(!labels.length)return false;var meaningful=/approve|authorize|review evidence|validation evidence|retry|repair|provide context|provide repository|upload|merge|deploy|rollback|reject|resume|continue mission|open pull request|review pr/;return labels.some(function(label){return meaningful.test(label)})}
  function gateActionCards(root){var cards=[];if(root&&root.matches&&root.matches('.br-actions-card'))cards.push(root);if(root&&root.querySelectorAll)cards=cards.concat(Array.from(root.querySelectorAll('.br-actions-card')));cards.forEach(function(card){if(!meaningfulActionCard(card))card.remove()})}
  function installIdentity(){document.querySelectorAll('.br-name').forEach(function(node){if(/^Board Room\b/.test(node.textContent||'')){var time=node.querySelector('.br-time');node.textContent='Jarvis ';if(time)node.appendChild(time)}});document.querySelectorAll('.br-msg.board .br-avatar').forEach(function(node){node.textContent='J'});var input=byId('message');if(input)input.placeholder='Message Jarvis...';document.querySelectorAll('.br-header .brand-small').forEach(function(node){if(node.textContent.trim()==='Board Room')node.textContent='Jarvis'});var heading=document.querySelector('.br-header h2');if(heading)heading.textContent='Executive AI';document.querySelectorAll('[data-section="board"]').forEach(function(node){node.textContent=node.textContent.replace('Board Room','Jarvis')});var openButton=byId('openBoardBtn');if(openButton)openButton.textContent='Jarvis'}
  function installComposer(){var input=byId('message');if(!input||byId('jarvisAttachmentInput'))return;var composer=input.closest('.br-composer');if(!composer)return;var button=document.createElement('button');button.type='button';button.className='jarvis-attach-button';button.setAttribute('aria-label','Attach files');button.title='Attach files';button.textContent='+';var picker=document.createElement('input');picker.type='file';picker.id='jarvisAttachmentInput';picker.multiple=true;picker.hidden=true;picker.accept='.txt,.md,.json,.csv,.xml,.yaml,.yml,.toml,.ini,.log,.py,.js,.jsx,.ts,.tsx,.css,.html,.sql,.sh,.java,.go,.rs,.rb,.php,.c,.h,.cpp,.hpp,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.webp';button.onclick=function(){picker.click()};picker.onchange=function(){addFiles(picker.files);picker.value=''};var preview=document.createElement('div');preview.id='jarvisAttachments';preview.className='jarvis-attachments';var error=document.createElement('div');error.id='jarvisAttachmentError';error.className='jarvis-attachment-error';composer.insertBefore(button,input);composer.appendChild(picker);composer.appendChild(preview);composer.appendChild(error);input.addEventListener('input',function(){localStorage.setItem(DRAFT_KEY,input.value||'');markActiveState('draft')});restoreDraft();composer.addEventListener('dragover',function(event){event.preventDefault();composer.classList.add('jarvis-drop-active')});composer.addEventListener('dragleave',function(){composer.classList.remove('jarvis-drop-active')});composer.addEventListener('drop',function(event){event.preventDefault();composer.classList.remove('jarvis-drop-active');addFiles(event.dataTransfer&&event.dataTransfer.files)})}
  function installChatWrapper(){if(!window.boardRoomChat||window.__jarvisAttachmentWrapper)return;window.__jarvisAttachmentWrapper=true;var original=window.boardRoomChat;window.boardRoomChat=async function(){var input=byId('message');var text=String(input&&input.value||'').trim();if(!text&&!pendingAttachments.length)return;if(pendingAttachments.length){var attachmentBlock='\n\nAttachments supplied to Jarvis:\n'+pendingAttachments.map(function(item){return '- '+item.name+' ('+item.mime_type+', '+sizeLabel(item.size)+')'}).join('\n');if(input)input.value=(text||'Please review the attached files.')+attachmentBlock;window.__jarvisPendingAttachments=pendingAttachments.map(attachmentSummary)}clearDraft();markActiveState('active');var result=await original.apply(this,arguments);pendingAttachments=[];window.__jarvisPendingAttachments=[];renderAttachments();return result}
    var nativeFetch=window.fetch;window.fetch=function(input,init){try{var url=typeof input==='string'?input:(input&&input.url||'');if(url.indexOf('/mission-control/operating-console/chat')>=0&&init&&typeof init.body==='string'&&window.__jarvisPendingAttachments&&window.__jarvisPendingAttachments.length){var body=JSON.parse(init.body);body.attachments=window.__jarvisPendingAttachments;init=Object.assign({},init,{body:JSON.stringify(body)})}}catch(error){}return nativeFetch.call(this,input,init)}
  }
  function installLifecycle(){if(window.__jarvisLifecycleInstalled||!window.newBoardChat)return;window.__jarvisLifecycleInstalled=true;var originalNewChat=window.newBoardChat;window.newBoardChat=function(){archiveActiveSession();clearDraft();pendingAttachments=[];renderAttachments();var result=originalNewChat.apply(this,arguments);var input=byId('message');if(input)input.value='';return result};document.querySelectorAll('.logout,#logoutBtn').forEach(function(button){button.addEventListener('click',function(){archiveActiveSession();clearDraft();sessionStorage.removeItem(TAB_KEY)})})}
  function install(){installIdentity();installComposer();installChatWrapper();installLifecycle();gateActionCards(document)}
  document.addEventListener('DOMContentLoaded',function(){install();var observer=new MutationObserver(function(records){records.forEach(function(record){Array.from(record.addedNodes||[]).forEach(function(node){if(node.nodeType===1){gateActionCards(node);installIdentity();installComposer();installChatWrapper();installLifecycle()}})})});observer.observe(document.body,{childList:true,subtree:true})});
})();
</script>
"""


def enhance_dashboard_with_jarvis(html: str) -> str:
    """Apply the Jarvis identity and progressive chat enhancements to the existing UI."""
    enhanced = html.replace("</head>", JARVIS_STYLE + "</head>", 1)
    return enhanced.replace("</body>", JARVIS_SCRIPT + "</body>", 1)
