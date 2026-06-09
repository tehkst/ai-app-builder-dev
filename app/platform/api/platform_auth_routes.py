from __future__ import annotations

from typing import Dict

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.platform.api.security import platform_admin_login


router = APIRouter(prefix="/platform/auth", tags=["platform-auth"])


class PlatformAdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


@router.post("/login")
def login_platform_admin(payload: PlatformAdminLoginRequest) -> Dict[str, str]:
    return platform_admin_login(
        username=payload.username,
        password=payload.password,
        route="/platform/auth/login",
    )


@router.get("/login-page", response_class=HTMLResponse)
def platform_admin_login_page() -> str:
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>AI Software Factory — Platform Login</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 40px; background: #f8fafc; color: #0f172a; }
    .card { max-width: 520px; background: white; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }
    label { display: block; margin-top: 16px; font-weight: 700; }
    input { width: 100%; box-sizing: border-box; margin-top: 6px; padding: 12px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 15px; }
    button { margin-top: 18px; padding: 12px 16px; border: 0; border-radius: 10px; background: #2563eb; color: white; font-weight: 800; cursor: pointer; }
    button.secondary { background: #475569; margin-left: 8px; }
    pre { margin-top: 16px; padding: 12px; background: #0f172a; color: #e2e8f0; border-radius: 10px; white-space: pre-wrap; }
    .muted { color: #64748b; font-size: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>AI Software Factory</h1>
    <p class="muted">Private MVP platform admin login. The JWT is stored only in this browser's localStorage.</p>

    <label>Platform Admin Username</label>
    <input id="username" autocomplete="username" />

    <label>Platform Admin Password</label>
    <input id="password" type="password" autocomplete="current-password" />

    <button onclick="login()">Login</button>
    <button class="secondary" onclick="clearToken()">Clear Token</button>

    <pre id="status">Not logged in.</pre>
  </div>

<script>
async function login() {
  const status = document.getElementById('status');
  status.textContent = 'Logging in...';

  try {
    const response = await fetch('/platform/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: document.getElementById('username').value,
        password: document.getElementById('password').value
      })
    });

    const data = await response.json();

    if (!response.ok) {
      status.textContent = 'Login failed:\\n' + JSON.stringify(data, null, 2);
      return;
    }

    localStorage.setItem('platform_admin_jwt', data.access_token);
    localStorage.setItem('platform_auth_mode', 'jwt_bearer');

    status.textContent = 'Login successful. Opening dashboard...';
    window.location.href = '/platform/app-build/dashboard';
  } catch (err) {
    status.textContent = 'Login error: ' + String(err);
  }
}

function clearToken() {
  localStorage.removeItem('platform_admin_jwt');
  localStorage.removeItem('platform_auth_mode');
  status.textContent = 'Token cleared.';
}
</script>
</body>
</html>
"""
