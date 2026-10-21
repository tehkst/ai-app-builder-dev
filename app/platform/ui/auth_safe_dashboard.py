from __future__ import annotations

import html
import logging
import traceback

logger = logging.getLogger(__name__)


def render_auth_safe_dashboard() -> str:
    """Render Mission Control without allowing dashboard failures to block access.

    This module is intentionally small and dependency-light. It exists so the
    authenticated UI shell can still load if a feature module such as Board Room,
    Conversation Intelligence, or Workflow rendering fails during import or render.
    """
    try:
        from app.platform.ui.mission_control import render_dashboard

        return render_dashboard()
    except Exception as exc:  # pragma: no cover - exercised by production safety path
        logger.exception("Mission Control dashboard render failed; serving safe shell.")
        return render_dashboard_fallback(exc)


def render_auth_safe_mission_control() -> str:
    """The same protection for the redesigned Mission Control (`ui/mc2`, the default page)."""
    try:
        from app.platform.ui.mc2 import render_mission_control_v2

        return render_mission_control_v2()
    except Exception as exc:  # pragma: no cover - exercised by login_boundary_check
        logger.exception("Mission Control (redesign) render failed; serving safe shell.")
        return render_dashboard_fallback(exc)


def render_dashboard_fallback(error: Exception) -> str:
    safe_error = html.escape(type(error).__name__)
    safe_detail = html.escape(str(error)[:500])
    safe_trace = html.escape("\n".join(traceback.format_exception_only(type(error), error)).strip())
    return f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Mission Control Safe Mode</title>
  <style>
    body{{margin:0;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#08111f;color:#e5eefb}}
    .shell{{max-width:960px;margin:0 auto;padding:32px}}
    .card{{border:1px solid #23314d;background:#101b2f;border-radius:18px;padding:22px;margin:18px 0}}
    .ok{{color:#22c55e;font-weight:800}} .warn{{color:#fbbf24;font-weight:800}}
    code,pre{{background:#07101e;border:1px solid #23314d;border-radius:12px;padding:12px;display:block;white-space:pre-wrap;color:#c7d2fe}}
    a{{color:#93c5fd}}
  </style>
</head>
<body>
  <main class='shell'>
    <h1>Mission Control Safe Mode</h1>
    <p class='ok'>Login boundary is active. You are past the public login surface.</p>
    <section class='card'>
      <h2>Dashboard module failed to render</h2>
      <p>The dashboard/Board Room layer failed, but login access was preserved.</p>
      <p><strong>Error:</strong> {safe_error}</p>
      <pre>{safe_detail or safe_trace}</pre>
    </section>
    <section class='card'>
      <h2>Safe endpoints</h2>
      <p><a href='/login'>Back to login</a> · <a href='/mission-control/ui'>Mission Control</a> · <a href='/health'>Health</a> · <a href='/ready'>Readiness</a> · <a href='/mission-control/auth'>Auth summary</a> · <a href='/mission-control'>Mission Control API</a></p>
    </section>
    <section class='card'>
      <h2>Operating rule</h2>
      <p class='warn'>Feature UI failures must never block login or authenticated access again.</p>
    </section>
  </main>
</body>
</html>"""
