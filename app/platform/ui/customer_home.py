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
.muted{color:#8a8d98;font-size:14px}
.row{display:flex;justify-content:space-between;border-top:1px solid #f1e9df;padding:12px 0}
.row:first-child{border-top:0}
.tag{display:inline-flex;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:800;background:#eaf1fe;color:#2b6df6}
</style>
</head>
<body>
<header class="topbar"><a class="brand" href="/"><span class="mark"></span><span>AI Software Factory</span></a><button class="logout" onclick="logout()">Logout</button></header>
<main>
<div class="card"><h1 id="welcomeHeading">Welcome</h1><p class="muted">This is your workspace home. More of your own dashboard is on the way.</p></div>
<div class="card"><div class="row"><span>Email</span><span id="fieldEmail" class="tag">Loading…</span></div><div class="row"><span>Name</span><span id="fieldName" class="tag">Loading…</span></div></div>
</main>
<script>
(function(){
var token=localStorage.getItem('customer_token')||'';
if(!token){window.location.href='/';return}
fetch('/api/auth/me',{headers:{'Authorization':'Bearer '+token}}).then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(function(data){
document.getElementById('welcomeHeading').textContent='Welcome, '+(data.full_name||data.email);
document.getElementById('fieldEmail').textContent=data.email||'Unknown';
document.getElementById('fieldName').textContent=data.full_name||'Unknown';
}).catch(function(){window.location.href='/'});
window.logout=function(){localStorage.removeItem('customer_token');window.location.href='/'};
})();
</script>
</body>
</html>
"""
