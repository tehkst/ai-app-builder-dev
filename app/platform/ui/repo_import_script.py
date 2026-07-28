from __future__ import annotations


REPO_IMPORT_CARD = (
    '<div class="card" id="repoImportCard"><h2>Imported Repositories</h2>'
    '<p class="muted">Connect an external GitHub repository so Jarvis can read and discuss it. Read-only for now - no write-back yet.</p>'
    '<div class="row"><input id="repoImportOwner" placeholder="owner (e.g. octocat)"><input id="repoImportRepo" placeholder="repo (e.g. Hello-World)"></div>'
    '<div class="row"><select id="repoImportCredential"><option value="GITHUB_IMPORT_TOKEN">GitHub Token (imported repositories)</option>'
    '<option value="GITHUB_TOKEN">GitHub Token (platform repository)</option></select>'
    '<button class="primary" id="repoImportBtn">Import</button></div>'
    '<p class="muted" id="repoImportStatus"></p>'
    '<div id="repoImportList">Loading…</div></div>'
)


def render_repo_import_script() -> str:
    return r"""
<script>
(function(){
  function byId(id){return document.getElementById(id)}
  function token(){return localStorage.getItem('mission_control_token')||''}
  function safe(s){return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  async function post(url,body){var r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
  function repoRowHtml(repo){
    var entries=(repo.top_level_entries||[]).slice(0,8).map(function(e){return safe(e.name)+(e.type==='dir'?'/':'')}).join(', ');
    return '<div class="row" style="flex-direction:column;align-items:stretch;gap:4px;padding:8px 0">'
      +'<div style="display:flex;justify-content:space-between;align-items:center"><strong>'+safe(repo.full_name)+'</strong>'
      +'<button class="secondary" data-action="remove" data-name="'+safe(repo.full_name)+'">Remove</button></div>'
      +'<span class="muted" style="font-size:12px">Default branch: '+safe(repo.default_branch||'unknown')+' · '+safe(repo.status)+'</span>'
      +(entries?'<span class="muted" style="font-size:12px">'+entries+'</span>':'')
      +'</div>';
  }
  async function loadRepos(){
    var box=byId('repoImportList'); if(!box)return;
    try{
      var data=await post('/mission-control/repo-import/list',{token:token()});
      if(data.status!=='ready'){box.innerHTML='<p class="muted">'+safe(data.error||'Could not load imported repositories.')+'</p>';return}
      var repos=data.repositories||[];
      box.innerHTML=repos.length?repos.map(repoRowHtml).join(''):'<p class="muted">No repositories connected yet.</p>';
      Array.from(document.querySelectorAll('#repoImportList [data-action="remove"]')).forEach(function(btn){
        btn.onclick=async function(){
          btn.disabled=true;
          try{await post('/mission-control/repo-import/remove',{token:token(),full_name:btn.dataset.name});loadRepos()}
          finally{btn.disabled=false}
        };
      });
    }catch(e){box.innerHTML='<p class="muted">Could not load imported repositories.</p>'}
  }
  async function doImport(){
    var owner=(byId('repoImportOwner').value||'').trim();
    var repo=(byId('repoImportRepo').value||'').trim();
    var credentialKey=byId('repoImportCredential').value;
    var status=byId('repoImportStatus');
    if(!owner||!repo){status.textContent='Enter both owner and repo.';return}
    var btn=byId('repoImportBtn'); btn.disabled=true; status.textContent='Connecting…';
    try{
      var data=await post('/mission-control/repo-import/connect',{token:token(),owner:owner,repo:repo,credential_key_name:credentialKey});
      if(data.status==='connected'){status.textContent='Connected '+data.full_name+' (branch: '+data.default_branch+').';byId('repoImportOwner').value='';byId('repoImportRepo').value='';loadRepos()}
      else{status.textContent=data.error||'Could not connect to that repository.'}
    }catch(e){status.textContent='Could not connect to that repository.'}
    finally{btn.disabled=false}
  }
  document.addEventListener('DOMContentLoaded',function(){
    var btn=byId('repoImportBtn'); if(btn)btn.addEventListener('click',doImport);
    var nav=document.querySelector('[data-section="settings"]');
    if(nav)nav.addEventListener('click',function(){setTimeout(loadRepos,50)});
    if(window.location.hash==='#settings')loadRepos();
  });
  window.loadImportedRepos=loadRepos;
})();
</script>
"""
