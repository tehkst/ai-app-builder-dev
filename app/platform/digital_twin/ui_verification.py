from __future__ import annotations

import base64
import http.server
import os
import socket
import socketserver
import threading
import time
from typing import Any, Dict, List

MAX_CLICK_STEPS = 20
PAGE_LOAD_TIMEOUT_MS = 15000


def execute_ui_ux_verification(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Serve a candidate static app directory locally and drive headless Chromium
    against it to verify it loads cleanly before founder approval.

    Scoped to static generated apps (HTML/CSS/JS, e.g. a SaaS Builder reference
    app) served read-only from a workspace directory - this does not start a
    second copy of the platform's own FastAPI service.
    """
    source_directory = str(payload.get("source_directory") or "").strip()
    if not source_directory or not os.path.isdir(source_directory):
        return {"status": "failed", "error": "source_directory must be an existing directory."}
    entry_file = str(payload.get("entry_file") or "index.html").lstrip("/")
    click_steps = payload.get("click_steps") if isinstance(payload.get("click_steps"), list) else []
    init_script = payload.get("init_script")
    init_script = str(init_script) if isinstance(init_script, str) and init_script.strip() else None
    capture_layout_metrics = bool(payload.get("capture_layout_metrics"))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"status": "failed", "error": "Playwright is not available in this runtime."}

    port = _free_port()
    httpd, server_thread = _start_static_server(source_directory, port)
    console_errors: List[str] = []
    screenshot_base64 = None
    layout_metrics = None
    try:
        with sync_playwright() as pw:
            # No executable_path override by default - Playwright resolves its own
            # installed browser (matches the version pinned in requirements.txt via
            # `playwright install --with-deps chromium` in the Dockerfile). Only set
            # PLAYWRIGHT_CHROMIUM_EXECUTABLE when the installed browser cache doesn't
            # match the installed playwright package version (e.g. a dev sandbox with
            # a pre-baked browser pinned to a different revision).
            browser = pw.chromium.launch(
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
                args=["--no-sandbox"],
            )
            page = browser.new_page()
            if init_script:
                page.add_init_script(script=init_script)
            page.on("console", lambda message: _record_console_error(console_errors, message))
            page.on("pageerror", lambda exc: console_errors.append("uncaught exception: %s" % exc))
            page.goto("http://127.0.0.1:%d/%s" % (port, entry_file), timeout=PAGE_LOAD_TIMEOUT_MS)
            for step in click_steps[:MAX_CLICK_STEPS]:
                if not isinstance(step, dict):
                    continue
                selector = str(step.get("selector") or "").strip()
                if not selector:
                    continue
                action = str(step.get("action") or "click")
                try:
                    if action == "fill":
                        page.fill(selector, str(step.get("value") or ""), timeout=5000)
                    else:
                        page.click(selector, timeout=5000)
                    page.wait_for_timeout(250)
                except Exception as exc:
                    console_errors.append("interaction_error(%s): %s" % (selector, type(exc).__name__))
            if capture_layout_metrics:
                try:
                    layout_metrics = page.evaluate(_LAYOUT_METRICS_SCRIPT)
                except Exception as exc:
                    console_errors.append("layout_metrics_error: %s" % type(exc).__name__)
            screenshot_bytes = page.screenshot()
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode("ascii")
            browser.close()
    except Exception as exc:
        return {"status": "failed", "error": "UI verification could not run: %s" % type(exc).__name__}
    finally:
        httpd.shutdown()
        server_thread.join(timeout=5)

    passed = not console_errors
    result = {
        "status": "completed" if passed else "failed",
        "console_errors": console_errors[:20],
        "screenshot_base64": screenshot_base64,
        "error": None if passed else "%d console error(s) were captured." % len(console_errors),
    }
    if capture_layout_metrics:
        result["layout_metrics"] = layout_metrics
    return result


# Captures bounding-box + key computed-style properties for every element with an id, plus
# every button, keyed so two renders of the same page (before/after a proposed change) can be
# compared value-for-value. This is what lets a UI/UX check detect a change that compiled and
# rendered without error but produced no actual visible difference - e.g. a CSS edit to a
# property that a later stylesheet re-declares, or one that isn't the real constraint on an
# element's rendered size - instead of only catching outright console errors.
_LAYOUT_METRICS_SCRIPT = """
() => {
  var out = {};
  var seen = new Set();
  function record(el, key) {
    if (!el || seen.has(el)) return;
    seen.add(el);
    var rect = el.getBoundingClientRect();
    var style = getComputedStyle(el);
    out[key] = {
      // The rendered bounding box is the ground truth for "did this actually change" - it's
      // what the layout engine resolved AFTER applying every constraint. Declared constraint
      // properties like min-width/max-width are deliberately NOT compared: their resolved
      // string value changes whenever the source CSS changes even when they were never the
      // binding constraint, which would make an invisible edit look "different" here too.
      x: Math.round(rect.x), y: Math.round(rect.y),
      w: Math.round(rect.width * 100) / 100, h: Math.round(rect.height * 100) / 100,
      padding: style.padding, margin: style.margin, fontSize: style.fontSize,
      display: style.display, gridTemplateColumns: style.gridTemplateColumns,
      color: style.color, backgroundColor: style.backgroundColor,
      // Geometry alone misses changes that are purely textual (a label, a placeholder, a
      // heading) - these catch that a founder would still see even when no box moved or
      // resized.
      text: (el.textContent || '').trim().slice(0, 300),
      placeholder: el.placeholder || null,
      value: (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? (el.value || '') : null,
      src: el.getAttribute ? el.getAttribute('src') : null,
      alt: el.getAttribute ? el.getAttribute('alt') : null
    };
  }
  document.querySelectorAll('[id]').forEach(function(el) { record(el, '#' + el.id) });
  document.querySelectorAll('button').forEach(function(el, i) {
    record(el, 'button:' + i + ':' + (el.textContent || '').trim().slice(0, 24));
  });
  return out;
}
"""


_NOISE_PATTERNS = ("failed to load resource", "favicon.ico")


def _record_console_error(console_errors: List[str], message: Any) -> None:
    if message.type != "error":
        return
    lowered = message.text.lower()
    if any(pattern in lowered for pattern in _NOISE_PATTERNS):
        return
    console_errors.append(message.text)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _start_static_server(directory: str, port: int):
    def handler_factory(*args, **kwargs):
        return http.server.SimpleHTTPRequestHandler(*args, directory=directory, **kwargs)

    httpd = socketserver.TCPServer(("127.0.0.1", port), handler_factory)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    return httpd, thread
