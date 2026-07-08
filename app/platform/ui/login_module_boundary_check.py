from __future__ import annotations

from pathlib import Path


def main() -> None:
    dashboard = Path("app/platform/ui/founder_dashboard_stable.py").read_text()
    login_module = Path("app/platform/ui/login_module.py").read_text()

    template_engine = Path("app/platform/ui/dashboard_template_engine.py").read_text()
    if "render_login_screen" not in template_engine:
        raise SystemExit("Dashboard template engine missing render_login_screen integration")
    browser_script = Path("app/platform/ui/dashboard_browser_script.py").read_text()

    required_dashboard_markers = [
        "__LOGIN_SCREEN__",
        "__DASHBOARD_BROWSER_SCRIPT__",
    ]
    for marker in required_dashboard_markers:
        if marker not in dashboard:
            raise SystemExit(f"Missing login module integration marker: {marker}")

    forbidden_dashboard_fragments = [
        "async function login()",
        "async function verifySession()",
        "mission_control_token')||''",
        "id=\"loginScreen\" class=\"login-screen\"",
    ]
    for fragment in forbidden_dashboard_fragments:
        if fragment in dashboard:
            raise SystemExit(f"Login/auth code leaked back into dashboard shell: {fragment}")


    required_browser_script_fragments = [
        "__LOGIN_SCRIPT__",
        "render_login_script",
        "render_dashboard_browser_script",
    ]
    for fragment in required_browser_script_fragments:
        if fragment not in browser_script:
            raise SystemExit(f"Dashboard browser script missing required login integration: {fragment}")

    required_login_fragments = [
        "async function login()",
        "async function verifySession()",
        "bindLoginModule",
        "mission_control_token",
        "/mission-control/auth/login",
        "/mission-control/auth/session",
    ]
    for fragment in required_login_fragments:
        if fragment not in login_module:
            raise SystemExit(f"Standalone login module missing required fragment: {fragment}")

    print("login module boundary ok")


if __name__ == "__main__":
    main()
