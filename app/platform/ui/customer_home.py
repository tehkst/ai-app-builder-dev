from __future__ import annotations


def render_customer_home() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AI Software Factory · Customer Home</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#2b2d33;background:#fbf7f2}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 50% 0,#fff 0,#fbf7f2 45%,#f6eee5 100%)}
a{color:inherit;text-decoration:none}
.topbar{height:70px;display:flex;align-items:center;justify-content:space-between;padding:0 6vw}
.brand{display:flex;align-items:center;gap:10px;font-weight:900;font-size:22px;letter-spacing:-.03em}
.mark{width:26px;height:26px;border-radius:8px;background:linear-gradient(135deg,#2b6df6,#6ee7ff)}
.logout{border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:999px;padding:9px 16px;font-weight:800;cursor:pointer}
main{max-width:760px;margin:0 auto;padding:40px 20px 80px}
.card{background:white;border:1px solid #eadfd5;border-radius:20px;padding:26px;margin-bottom:16px;box-shadow:0 18px 60px rgba(30,26,23,.06)}
h1{font-size:32px;letter-spacing:-.03em;margin:0 0 6px}
h2{font-size:18px;margin:0 0 4px}
.muted{color:#8a8d98;font-size:14px}
.row{display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f1e9df;padding:12px 0;gap:12px}
.row:first-child{border-top:0}
.tag{display:inline-flex;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:800;background:#eaf1fe;color:#2b6df6}
label{display:block;font-size:13px;color:#686b75;margin:14px 0 6px}
.field{width:100%;border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:12px;padding:12px;font:inherit}
.actions{display:flex;gap:10px;margin-top:14px}
button.primary{border:0;border-radius:12px;padding:12px 18px;font-weight:800;background:#2b6df6;color:white;cursor:pointer}
button.danger{border:1px solid #f1c9c9;background:#fff5f5;color:#c93b3b;border-radius:10px;padding:7px 12px;font-weight:700;cursor:pointer;font-size:12.5px}
.error{color:#cf3d3d;font-size:13px;margin-top:10px;min-height:18px}
.note{font-size:13px;margin-top:10px;color:#8a8d98}
.warn-banner{background:#fff7e6;border:1px solid #f2d999;color:#8a5a00;border-radius:12px;padding:12px 14px;font-size:13px;margin-bottom:14px}
.secret-name{font-weight:700}
.secret-meta{font-size:12px;color:#8a8d98}
.empty{color:#8a8d98;font-size:13px}
</style>
</head>
<body>
<header class="topbar"><a class="brand" href="/"><span class="mark"></span><span>AI Software Factory</span></a><button class="logout" onclick="logout()">Logout</button></header>
<main>
<div class="card"><h1 id="welcomeHeading">Welcome</h1><p class="muted">This is your workspace home. More of your own dashboard is on the way.</p></div>
<div class="card"><div class="row"><span>Email</span><span id="fieldEmail" class="tag">Loading…</span></div><div class="row"><span>Name</span><span id="fieldName" class="tag">Loading…</span></div></div>
<div class="card">
<h2>API Keys &amp; Secrets</h2>
<p class="muted">Store your own third-party API keys (OpenAI, Stripe, etc.) for use in your builds. Values are encrypted before they're ever saved and are never shown again — only the name and dates are kept visible.</p>
<div id="vaultWarning" class="warn-banner" style="display:none">Secret storage is not yet configured on this deployment. Saving is temporarily disabled.</div>
<div id="secretsList"><p class="empty">Loading…</p></div>
<label>Key name</label><input class="field" id="secretKeyName" placeholder="OPENAI_API_KEY" autocomplete="off"/>
<label>Value</label><input class="field" id="secretValue" type="password" placeholder="Paste the secret value" autocomplete="off"/>
<div class="actions"><button class="primary" id="saveSecretBtn" onclick="saveSecret()">Save secret</button></div>
<div id="secretError" class="error"></div>
</div>
</main>
<script>
(function(){
var token=localStorage.getItem('customer_token')||'';
if(!token){window.location.href='/';return}
function authHeaders(){return {'Authorization':'Bearer '+token,'Content-Type':'application/json'}}
fetch('/api/auth/me',{headers:authHeaders()}).then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(function(data){
document.getElementById('welcomeHeading').textContent='Welcome, '+(data.full_name||data.email);
document.getElementById('fieldEmail').textContent=data.email||'Unknown';
document.getElementById('fieldName').textContent=data.full_name||'Unknown';
}).catch(function(){window.location.href='/'});
window.logout=function(){localStorage.removeItem('customer_token');window.location.href='/'};

function renderSecrets(data){
  var list=document.getElementById('secretsList');
  var warning=document.getElementById('vaultWarning');
  warning.style.display=data.configured?'none':'block';
  document.getElementById('saveSecretBtn').disabled=!data.configured;
  var secrets=data.secrets||[];
  if(!secrets.length){list.innerHTML='<p class="empty">No secrets stored yet.</p>';return}
  list.innerHTML='';
  secrets.forEach(function(secret){
    var row=document.createElement('div');
    row.className='row';
    var meta='Added '+new Date(secret.created_at).toLocaleDateString()+(secret.last_used_at?(' · last used '+new Date(secret.last_used_at).toLocaleDateString()):' · never used');
    row.innerHTML='<div><div class="secret-name">'+escapeHtml(secret.key_name)+'</div><div class="secret-meta">'+escapeHtml(meta)+'</div></div><div><span class="tag">••••••••</span> <button class="danger" onclick="deleteSecret(\\''+escapeHtml(secret.key_name)+'\\')">Delete</button></div>';
    list.appendChild(row);
  });
}
function escapeHtml(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
window.refreshSecrets=function(){
  fetch('/api/secrets',{headers:authHeaders()}).then(function(r){return r.json()}).then(renderSecrets).catch(function(){
    document.getElementById('secretsList').innerHTML='<p class="empty">Could not load secrets.</p>';
  });
};
window.saveSecret=async function(){
  var err=document.getElementById('secretError');err.textContent='';
  var keyName=document.getElementById('secretKeyName').value.trim();
  var value=document.getElementById('secretValue').value;
  try{
    var response=await fetch('/api/secrets',{method:'POST',headers:authHeaders(),body:JSON.stringify({key_name:keyName,value:value})});
    var data=await response.json();
    if(!response.ok){err.textContent=data.detail||'Could not save secret.';return}
    document.getElementById('secretKeyName').value='';
    document.getElementById('secretValue').value='';
    refreshSecrets();
  }catch(error){err.textContent='Request failed: '+error}
};
window.deleteSecret=async function(keyName){
  if(!confirm('Delete '+keyName+'? This cannot be undone.'))return;
  try{
    await fetch('/api/secrets/'+encodeURIComponent(keyName),{method:'DELETE',headers:authHeaders()});
    refreshSecrets();
  }catch(error){}
};
refreshSecrets();
})();
</script>
</body>
</html>
"""
