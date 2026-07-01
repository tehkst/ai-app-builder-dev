from __future__ import annotations

from html import escape

from app.platform.auth.service import build_auth_summary
from app.platform.founder_console.service import build_founder_console_summary


def render_public_landing() -> str:
    console = build_founder_console_summary()
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"
    return _page(show_login=False, ai_status=ai_status)


def render_login_page() -> str:
    console = build_founder_console_summary()
    ai_status = f"{console['runtime']['ai_provider']} · {console['runtime']['model']}"
    return _page(show_login=True, ai_status=ai_status)


def _page(*, show_login: bool, ai_status: str) -> str:
    auth = build_auth_summary()
    login_class = "modal-backdrop open" if show_login else "modal-backdrop"
    return f"""
<!doctype html>
<html lang='en'>
<head><meta charset='utf-8' /><meta name='viewport' content='width=device-width, initial-scale=1' /><title>AI Software Factory</title></head>
<body><h1>AI Software Factory</h1><p>{escape(ai_status)}</p><button onclick='openLogin()'>Log in</button><section id='loginModal' class='{login_class}'><h2>Log in to Mission Control</h2><p>{escape(auth['status'])}</p></section><script>function openLogin(){{document.getElementById('loginModal').className='modal-backdrop open';}}</script></body>
</html>
"""
