"""Mission Control sign-in (stage 5): founder email + password, and "forgot password".

Same endpoints as the classic login: POST /mission-control/auth/login ({email, password} ->
session.token, stored in localStorage "mission_control_token") and POST
/mission-control/auth/forgot-password. Shown by MC.toLogin() (home_script) when there is no valid
session; after signing in, MC.start() opens the app.
"""
from __future__ import annotations

LOGIN_HTML = """
<main class="mc-login" id="mcLogin" hidden>
  <form class="mc-card mc-login-card" id="mcLoginForm">
    <span class="mc-empty">AI Software Factory</span><h1>Mission Control</h1><p class="mc-empty">Owner sign-in.</p>
    <label>Email<input id="mcLoginEmail" type="email" autocomplete="username" required></label>
    <label>Password<input id="mcLoginPassword" type="password" autocomplete="current-password" required></label>
    <button type="submit" class="mc-btn" id="mcLoginBtn">Sign in</button>
    <p class="mc-status" id="mcLoginStatus" role="alert"></p>
    <button type="button" class="mc-btn quiet" id="mcForgotToggle">Forgot your password?</button>
  </form>
  <form class="mc-card mc-login-card" id="mcForgotForm" hidden>
    <h1>Reset your password</h1><p class="mc-empty">We’ll email you a reset link.</p>
    <label>Email<input id="mcForgotEmail" type="email" autocomplete="username" required></label>
    <button type="submit" class="mc-btn">Send reset link</button>
    <p class="mc-status" id="mcForgotStatus" aria-live="polite"></p>
    <button type="button" class="mc-btn quiet" id="mcBackToLogin">Back to sign-in</button>
  </form>
</main>
"""

LOGIN_SCRIPT = r"""
(function(){
  var MC=window.MC;var $=function(id){return document.getElementById(id)};
  function json(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()})}
  function swap(forgot){$('mcLoginForm').hidden=forgot;$('mcForgotForm').hidden=!forgot;(forgot?$('mcForgotEmail'):$('mcLoginEmail')).focus()}
  $('mcLoginForm').addEventListener('submit',async function(e){
    e.preventDefault();var btn=$('mcLoginBtn'),out=$('mcLoginStatus');btn.disabled=true;out.textContent='Signing in…';out.classList.remove('bad');
    try{var d=await json('/mission-control/auth/login',{email:$('mcLoginEmail').value,password:$('mcLoginPassword').value});
      if(!(d.session&&d.session.token))throw new Error(d.error||d.message||'Email or password is not right.');
      try{localStorage.setItem('mission_control_token',d.session.token)}catch(err){}
      $('mcLoginPassword').value='';out.textContent='';MC.start();
    }catch(err){out.textContent=err.message;out.classList.add('bad')}
    finally{btn.disabled=false}
  });
  $('mcForgotForm').addEventListener('submit',async function(e){
    e.preventDefault();var out=$('mcForgotStatus');out.textContent='Sending…';
    try{var d=await json('/mission-control/auth/forgot-password',{email:$('mcForgotEmail').value});out.textContent=d.message||'If that email exists, a reset link has been sent.'}
    catch(err){out.textContent='That didn’t go through: '+err.message}
  });
  $('mcForgotToggle').addEventListener('click',function(){swap(true)});
  $('mcBackToLogin').addEventListener('click',function(){swap(false)});
})();
"""
