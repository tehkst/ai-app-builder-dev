from __future__ import annotations

import html as html_module
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFile

FRONTEND_EXTENSIONS = (".jsx", ".tsx", ".js", ".ts")
EXCLUDED_PATH_HINTS = ("test", "backend/", "server/", "requirements.txt", "readme")

_REACT_CDN_SCRIPTS = (
    '<script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>\n'
    '<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>\n'
    '<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>'
)


def render_generated_app_preview(db: Session, *, workflow_run_id: Optional[str]) -> str:
    """Best-effort static rendering of a generated app's frontend, so a customer can
    see it before deciding to request publish.

    This platform never runs a real npm build (webpack/vite) or a live backend
    process for generated apps - files exist only as DB-preview rows (see
    generated_file_persistence_service, write_mode "db_preview_only"). So this
    in-browser-transpiles the generated frontend entry component with Babel
    standalone and mounts it directly, instead of a real bundled build. It cannot
    resolve cross-file imports or live backend calls - both are called out in the
    rendered banner - so this is a UI/layout preview, not a fully working app.
    Full functionality requires the backend that only exists once published.
    """

    if not workflow_run_id:
        return _shell_message("This project hasn't started a build yet, so there's nothing to preview.")

    files = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .all()
    )
    if not files:
        return _shell_message("No generated files were found for this build yet.")

    css_files = [file_row for file_row in files if (file_row.language or "").lower() == "css"]
    entry = _pick_frontend_entry(files)
    if entry is None:
        return _shell_message(
            "Couldn't find a previewable frontend file in this build. "
            "Open the Details tab to see the generated file list."
        )

    component_source = _strip_module_syntax(entry.content_preview or "")
    mount_target = _detect_mount_identifier(component_source)
    inline_css = "\n".join(file_row.content_preview or "" for file_row in css_files)
    is_typescript = entry.path.lower().endswith((".ts", ".tsx"))

    parts: List[str] = []
    parts.append("<!doctype html>\n<html>\n<head>\n<meta charset=\"utf-8\"/>\n<title>Preview</title>\n")
    parts.append(_REACT_CDN_SCRIPTS)
    parts.append("\n<style>\n")
    parts.append(
        "body{margin:0;font-family:ui-sans-serif,system-ui,sans-serif}"
        ".preview-banner{background:#fff7e6;color:#8a5a00;font-size:12.5px;"
        "padding:8px 14px;border-bottom:1px solid #f2d999}"
        ".preview-fail{padding:24px;color:#c93b3b;font-family:ui-sans-serif,system-ui,sans-serif;"
        "white-space:pre-wrap}"
    )
    parts.append("\n")
    parts.append(inline_css)
    parts.append("\n</style>\n</head>\n<body>\n")
    parts.append(
        '<div class="preview-banner">Best-effort UI preview of %s &mdash; backend calls and '
        "cross-file imports aren't live here. Full functionality is available once this is "
        "published.</div>\n" % html_module.escape(entry.path)
    )
    parts.append('<div id="root"></div>\n')
    parts.append(
        "<script>\n"
        "(function(originalFetch){\n"
        "  window.fetch = function(){\n"
        "    return originalFetch.apply(this, arguments).catch(function(){\n"
        "      return Promise.resolve(new Response(JSON.stringify({preview: true, "
        'note: "Backend calls are not live in preview."}), '
        '{status: 200, headers: {"Content-Type": "application/json"}}));\n'
        "    });\n"
        "  };\n"
        "})(window.fetch);\n"
        "</script>\n"
    )
    # Deliberately NOT a <script type="text/babel"> auto-transform block: if the source
    # fails to *parse*, the browser's automatic transform just logs to console and runs
    # nothing at all - not even a try/catch placed inside that same block, since a parse
    # failure means none of the block's code ever executes. Calling Babel.transform
    # ourselves, in a plain script, lets a parse failure be caught exactly like a runtime
    # failure - so this can never silently render a blank page.
    parts.append('<script type="text/plain" id="preview-source">')
    parts.append(component_source.replace("</script", "<\\/script"))
    parts.append("</script>\n")
    parts.append("<script>\n")
    parts.append("(function(){\n")
    parts.append("  function showFailure(label, error){\n")
    parts.append("    document.getElementById('root').innerHTML =\n")
    parts.append("      '<div class=\"preview-fail\">' + label + ': ' +\n")
    parts.append("      String(error && error.message ? error.message : error).replace(/</g, '&lt;') + '</div>';\n")
    parts.append("  }\n")
    parts.append("  var source = document.getElementById('preview-source').textContent;\n")
    parts.append(
        "  var hookShim = 'const {useState,useEffect,useMemo,useCallback,useRef,"
        "useContext,useReducer,useLayoutEffect,Fragment} = React;\\n';\n"
    )
    parts.append("  var transformed;\n")
    parts.append("  try {\n")
    # runtime: 'classic' matters: the default 'automatic' JSX runtime makes Babel's
    # *output* itself contain `import { jsx as _jsx } from "react/jsx-runtime"` - which
    # then fails inside new Function() below (plain scripts can't use import either),
    # the same silent-blank failure mode this rewrite exists to fix. Classic runtime
    # compiles JSX straight to React.createElement(...) calls instead, no import needed.
    parts.append(
        "    transformed = Babel.transform(hookShim + source, {presets: [%s], filename: 'preview.%s'}).code;\n"
        % (
            "['react', {runtime: 'classic'}], 'typescript'" if is_typescript else "['react', {runtime: 'classic'}]",
            "tsx" if is_typescript else "jsx",
        )
    )
    parts.append("  } catch (parseError) {\n")
    parts.append("    showFailure('Could not parse this file for preview', parseError);\n")
    parts.append("    return;\n")
    parts.append("  }\n")
    parts.append("  try {\n")
    parts.append("    var run = new Function('React', 'ReactDOM', transformed + '\\nreturn %s;');\n" % mount_target)
    parts.append("    var Component = run(React, ReactDOM);\n")
    parts.append("    var root = ReactDOM.createRoot(document.getElementById('root'));\n")
    parts.append("    root.render(React.createElement(Component));\n")
    parts.append("  } catch (mountError) {\n")
    parts.append("    showFailure('Could not render a live preview of this component automatically', mountError);\n")
    parts.append("  }\n")
    parts.append("})();\n")
    parts.append("</script>\n</body>\n</html>")
    return "".join(parts)


_BOOTSTRAP_BASENAMES = ("index.js", "index.jsx", "index.ts", "index.tsx", "main.js", "main.jsx", "main.ts", "main.tsx")


def _basename(path: str) -> str:
    return path.lower().rsplit("/", 1)[-1]


def _defines_component(content: str) -> bool:
    return bool(re.search(r"(?:function|class)\s+[A-Z]\w*|const\s+[A-Z]\w*\s*=", content))


def _pick_frontend_entry(files: List[PlatformGeneratedFile]) -> Optional[PlatformGeneratedFile]:
    candidates = [
        file_row
        for file_row in files
        if file_row.path.lower().endswith(FRONTEND_EXTENSIONS)
        and not any(hint in file_row.path.lower() for hint in EXCLUDED_PATH_HINTS)
    ]
    if not candidates:
        return None
    # A conventional index.js/main.js only imports another file's component and mounts
    # it - since this preview can't resolve that cross-file import (see module docstring),
    # picking the bootstrap file directly always fails with "<Component> is not defined"
    # once the import is stripped: index.js has nothing left to render on its own. Prefer
    # a file that actually defines a component instead, and only fall back to a bootstrap
    # file (old behavior) when nothing else defines one - e.g. a single-file component
    # that both defines and mounts App in the same file.
    defining = [
        candidate for candidate in candidates
        if _basename(candidate.path) not in _BOOTSTRAP_BASENAMES
        and _defines_component(candidate.content_preview or "")
    ]
    if defining:
        named_app = [candidate for candidate in defining if _basename(candidate.path).startswith("app.")]
        pool = named_app or defining
        return max(pool, key=lambda file_row: len(file_row.content_preview or ""))
    for candidate in candidates:
        content = candidate.content_preview or ""
        if "createRoot" in content or "ReactDOM.render" in content:
            return candidate
    return max(candidates, key=lambda file_row: len(file_row.content_preview or ""))


def _strip_module_syntax(source: str) -> str:
    # DOTALL + non-greedy, matching from `import` to the first `;`, so a multi-line
    # `import {\n  useState,\n} from 'react';` is removed as one unit - a per-line regex
    # only strips the first line, leaving a dangling `import {` that fails to parse.
    without_imports = re.sub(r"import\s[^;]*?;", "", source, flags=re.DOTALL)
    without_default_export = re.sub(r"^\s*export\s+default\s+", "", without_imports, flags=re.MULTILINE)
    without_named_exports = re.sub(r"^\s*export\s+\{[^}]*\};?\s*$", "", without_default_export, flags=re.MULTILINE)
    return without_named_exports


def _detect_mount_identifier(source: str) -> str:
    for pattern in (r"function\s+(App)\s*\(", r"const\s+(App)\s*=", r"class\s+(App)\s+extends"):
        if re.search(pattern, source):
            return "App"
    match = re.search(r"function\s+([A-Z]\w*)\s*\(", source)
    if match:
        return match.group(1)
    match = re.search(r"const\s+([A-Z]\w*)\s*=", source)
    if match:
        return match.group(1)
    return "App"


def _shell_message(message: str) -> str:
    return (
        '<!doctype html>\n<html><head><meta charset="utf-8"/><style>\n'
        "body{font-family:ui-sans-serif,system-ui,sans-serif;color:#55585f;display:flex;"
        "align-items:center;justify-content:center;min-height:100vh;margin:0;background:#faf6f1}\n"
        ".box{max-width:420px;text-align:center;padding:24px}\n"
        "</style></head><body><div class=\"box\">%s</div></body></html>"
    ) % html_module.escape(message)
