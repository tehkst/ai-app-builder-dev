from __future__ import annotations

from html import escape


def render_reset_password_page(token: str, account_type: str) -> str:
    safe_token = escape(token or "")
    safe_type = "founder" if account_type == "founder" else "customer"
    endpoint = "/mission-control/auth/reset-password" if safe_type == "founder" else "/api/auth/reset-password"
    sign_in_href = "/admin" if safe_type == "founder" else "/"
    return f"""
<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>Reset password · AI Software Factory</title>
<style>
:root{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#2b2d33;background:#fbf7f2}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 50% 20%,#fff 0,#fbf7f2 45%,#f6eee5 100%)}}
a{{color:#2b6df6;text-decoration:none;font-weight:800}}
.login-card{{width:min(440px,92vw);background:#fffaf5;border:1px solid #e8ded4;border-radius:22px;padding:30px;box-shadow:0 30px 120px rgba(30,26,23,.2)}}
h2{{text-align:center;margin:0 0 18px;font-size:24px;letter-spacing:-.03em}}
label{{display:block;font-size:13px;color:#686b75;margin:14px 0 7px}}
.field{{width:100%;border:1px solid #eadfd5;background:white;color:#2b2d33;border-radius:14px;padding:14px;font:inherit}}
button{{width:100%;margin-top:18px;border:0;border-radius:14px;padding:14px;font-weight:800;background:#2b6df6;color:white;cursor:pointer}}
.note,.error{{font-size:13px;line-height:1.35;margin-top:14px;color:#8a8d98}}
.error{{color:#cf3d3d}}
</style>
</head>
<body>
<div class='login-card'>
<h2>Set a new password</h2>
<div id='formView'>
<label>New password</label><input class='field' id='newPassword' type='password' autocomplete='new-password'/>
<label>Confirm password</label><input class='field' id='confirmPassword' type='password' autocomplete='new-password'/>
<button onclick='submitReset()'>Reset password</button>
<div id='resetError' class='error'></div>
</div>
<div id='doneView' style='display:none'>
<p class='note' id='doneMessage'></p>
<p class='note'><a href='{sign_in_href}'>Back to sign in</a></p>
</div>
</div>
<script>
async function submitReset(){{
  var err=document.getElementById('resetError');err.textContent='';
  var pw=document.getElementById('newPassword').value;
  var confirm=document.getElementById('confirmPassword').value;
  if(pw!==confirm){{err.textContent='Passwords do not match.';return}}
  try{{
    var response=await fetch('{endpoint}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{token:'{safe_token}',new_password:pw}})}});
    var data=await response.json();
    if(response.ok&&(data.status==='ok'||data.access_token)){{
      document.getElementById('formView').style.display='none';
      document.getElementById('doneView').style.display='block';
      document.getElementById('doneMessage').textContent=data.message||'Password updated. You can now sign in.';
    }}else{{
      err.textContent=data.detail||data.error||'This reset link is invalid or has expired.';
    }}
  }}catch(error){{err.textContent='Request failed: '+error}}
}}
</script>
</body>
</html>
"""
