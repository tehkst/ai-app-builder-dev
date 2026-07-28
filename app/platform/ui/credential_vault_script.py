from __future__ import annotations


CREDENTIALS_CARD = (
    '<div class="card" id="credentialsCard"><h2>Credentials</h2>'
    '<p class="muted">Encrypted at rest via Cloud KMS. Values are masked by default; click Reveal to view.</p>'
    '<div id="credentialRows">Loading…</div></div>'
)


def render_credential_vault_script() -> str:
    return r"""
<script>
(function(){
  function byId(id){return document.getElementById(id)}
  function token(){return localStorage.getItem('mission_control_token')||''}
  function safe(s){return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  async function post(url,body){var r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
  var revealed={};
  function rowHtml(cred){
    var kn=cred.key_name;
    var shown=revealed[kn]?safe(revealed[kn]):safe(cred.masked_value);
    return '<div class="row" data-key="'+kn+'" style="flex-direction:column;align-items:stretch;gap:6px;padding:10px 0">'
      +'<div style="display:flex;justify-content:space-between;align-items:center"><strong>'+safe(cred.display_name)+'</strong><span class="muted" style="font-size:12px">'+safe(cred.source)+'</span></div>'
      +'<div style="display:flex;gap:8px;align-items:center"><code style="flex:1;word-break:break-all">'+shown+'</code>'
      +'<button class="secondary" data-action="reveal" data-key="'+kn+'">'+(revealed[kn]?'Hide':'Reveal')+'</button></div>'
      +'<div style="display:flex;gap:8px"><input type="password" placeholder="New value" data-input="'+kn+'" style="flex:1"><button class="primary" data-action="save" data-key="'+kn+'">Save</button></div>'
      +'</div>';
  }
  async function loadCredentials(){
    var box=byId('credentialRows'); if(!box)return;
    try{
      var data=await post('/mission-control/credentials/list',{token:token()});
      if(data.status!=='ready'){box.innerHTML='<p class="muted">'+safe(data.error||'Credentials unavailable.')+'</p>';return}
      var notice=data.vault_configured?'':'<p class="muted">Encryption at rest is not configured (KMS_KEY_NAME missing) — saving is disabled until it is.</p>';
      var rows=(data.credentials||[]).map(rowHtml).join('');
      box.innerHTML=notice+rows;
      wireRows();
    }catch(e){box.innerHTML='<p class="muted">Could not load credentials.</p>'}
  }
  function wireRows(){
    Array.from(document.querySelectorAll('#credentialRows [data-action="reveal"]')).forEach(function(btn){
      btn.onclick=async function(){
        var kn=btn.dataset.key;
        if(revealed[kn]){delete revealed[kn];loadCredentials();return}
        btn.disabled=true;
        try{
          var data=await post('/mission-control/credentials/reveal',{token:token(),key_name:kn});
          if(data.status==='revealed'){revealed[kn]=data.value;loadCredentials()}
          else{alert(data.error||'This credential is not configured.')}
        }finally{btn.disabled=false}
      };
    });
    Array.from(document.querySelectorAll('#credentialRows [data-action="save"]')).forEach(function(btn){
      btn.onclick=async function(){
        var kn=btn.dataset.key;
        var input=document.querySelector('#credentialRows [data-input="'+kn+'"]');
        var value=(input&&input.value||'').trim();
        if(!value)return;
        btn.disabled=true;
        try{
          var data=await post('/mission-control/credentials/save',{token:token(),key_name:kn,value:value});
          if(data.status==='saved'){if(input)input.value='';delete revealed[kn];loadCredentials()}
          else{alert(data.error||'Could not save credential.')}
        }finally{btn.disabled=false}
      };
    });
  }
  window.loadCredentials=loadCredentials;
  document.addEventListener('DOMContentLoaded',function(){
    var nav=document.querySelector('[data-section="settings"]');
    if(nav)nav.addEventListener('click',function(){setTimeout(loadCredentials,50)});
    if(window.location.hash==='#settings')loadCredentials();
  });
})();
</script>
"""
