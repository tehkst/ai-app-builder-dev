"""Endpoints a codebase defines, web requests it makes, and which request reaches which endpoint.

Pattern matching on comment-stripped source, never execution (the approach follows Floorplan, see
LICENSE-floorplan.txt). It catches most connections, not all; the Codebase Cartographer adds the
ones it can't see as explicit edges.

- Endpoints: Flask, FastAPI (router and blueprint prefixes in the same file, include_router and
  register_blueprint prefixes across files), Django urls.py, Express/Fastify/Koa/Hono (app.use
  mounts across files), Next.js route files and pages/api, Laravel routes, WordPress REST routes
  and admin-ajax actions.
- Requests: fetch, axios and similar clients, jQuery ajax, requests/httpx, wp_remote_*, curl_init
  and Laravel's Http facade. Template parts become wildcards; full URLs give the outside host.
- Matching: same number of path segments with wildcards matching anything, the method agreeing
  (ANY matches every method). When the request leaves out a base path kept in settings, a
  suffix match is used, but only if it is the only candidate.
"""
from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse

from app.platform.impact_map.parsers import strip_comments

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
NOT_HOSTS = re.compile(r"(^|\.)(w3\.org|schema\.org|example\.(com|org|net)|localhost|xmlns\.com|purl\.org|"
                       r"opensource\.org|apache\.org|mozilla\.org|semver\.org|json-schema\.org)$|^127\.|^0\.0\.0\.0$")


@dataclass
class Route:
    method: str  # GET, POST, ... or ANY
    path: str
    file: str
    line: int
    handler: str = ""

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"


@dataclass
class Request:
    method: str
    url: str  # as written, template parts replaced with *
    file: str
    line: int
    host: str = ""


@dataclass
class FileRoutes:
    routes: List[Route] = field(default_factory=list)
    requests: List[Request] = field(default_factory=list)
    hosts: Set[str] = field(default_factory=set)
    # router variable -> prefix declared in this file (Blueprint url_prefix, APIRouter prefix)
    own_prefix: Dict[str, str] = field(default_factory=dict)
    # (prefix, imported module specifier) for routers mounted from other files
    mounts: List[Tuple[str, str]] = field(default_factory=list)


def _line(code: str, pos: int) -> int:
    return code.count("\n", 0, pos) + 1


def _template(url: str) -> str:
    url = re.sub(r"\$\{(?:[^{}]|\{[^{}]*\})*\}", "*", url)  # JS template parts
    return re.sub(r"\{[^{}/]*\}", "*", url)  # Python f-string parts


def _host(url: str) -> str:
    if not re.match(r"https?://", url):
        return ""
    host = (urlparse(url).hostname or "").lower()
    return "" if not host or "*" in host or NOT_HOSTS.search(host) else host


def _path_of(url: str) -> str:
    return urlparse(url).path or "/" if re.match(r"https?://", url) else url.split("?")[0].split("#")[0]


# ---- Python ------------------------------------------------------------------------------------

_PY_DECORATOR = re.compile(r"@(\w+)\.(route|get|post|put|patch|delete|api_route)\(\s*(?:path\s*=\s*)?[rf]?(['\"])([^'\"]*)\3([^\n]*)")
_PY_DEF = re.compile(r"\n\s*(?:async\s+)?def\s+(\w+)")
_PY_PREFIX = re.compile(r"(\w+)\s*=\s*(?:\w+\.)?(Blueprint|APIRouter)\(([^)]*)\)")
_PY_PREFIX_ARG = re.compile(r"(?:url_prefix|prefix)\s*=\s*['\"]([^'\"]*)['\"]")
_PY_MOUNT = re.compile(r"\.(?:register_blueprint|include_router)\(\s*([\w.]+)([^)]*)\)")
_PY_IMPORT_FROM = re.compile(r"^[ \t]*from[ \t]+([\w.]+)[ \t]+import[ \t]+(\([^)]*\)|[\w \t,]+)", re.M)
_PY_IMPORT = re.compile(r"^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?", re.M)
_DJANGO_PATH = re.compile(r"\b(?:re_)?path\(\s*r?['\"]([^'\"]*)['\"]\s*,\s*([\w.]+)")
_PY_REQUEST = re.compile(r"\b(requests|httpx|session|client|http)\.(get|post|put|patch|delete|request)\(\s*"
                         r"(?:['\"](\w+)['\"]\s*,\s*)?[rf]?(['\"])([^'\"]+)\4", re.I)


def _python(path: str, source: str) -> FileRoutes:
    out = FileRoutes()
    code = strip_comments(source, hash_comments=True)
    names = _python_imports(code)
    for match in _PY_PREFIX.finditer(code):
        arg = _PY_PREFIX_ARG.search(match.group(3))
        out.own_prefix[match.group(1)] = arg.group(1) if arg else ""
    for match in _PY_DECORATOR.finditer(code):
        obj, verb, route, rest = match.group(1), match.group(2), match.group(4), match.group(5)
        if verb in ("route", "api_route"):
            listed = re.findall(r"['\"](GET|POST|PUT|PATCH|DELETE)['\"]", rest, re.I)
            methods = [m.upper() for m in listed] or (["GET"] if verb == "route" else ["ANY"])
        else:
            methods = [verb.upper()]
        handler = _PY_DEF.search(code, match.end())
        prefix = out.own_prefix.get(obj, "")
        for method in methods:
            out.routes.append(Route(method, _join(prefix, route), path, _line(code, match.start()),
                                    handler.group(1) if handler else ""))
    if posixpath.basename(path) == "urls.py":
        for match in _DJANGO_PATH.finditer(code):
            out.routes.append(Route("ANY", _join("", _django(match.group(1))), path, _line(code, match.start()),
                                    match.group(2)))
    for match in _PY_MOUNT.finditer(code):
        arg = _PY_PREFIX_ARG.search(match.group(2))
        module = names.get(match.group(1).split(".")[0])
        if arg and module:
            out.mounts.append((arg.group(1), module))
    for match in _PY_REQUEST.finditer(code):
        verb = match.group(2).upper()
        method = (match.group(3) or "GET").upper() if verb == "REQUEST" else verb
        _add_request(out, method, match.group(5), path, _line(code, match.start()))
    _collect_hosts(out, code)
    return out


def _python_imports(code: str) -> Dict[str, str]:
    """Local name -> module it came from (dotted, relative dots kept)."""
    names: Dict[str, str] = {}
    for match in _PY_IMPORT_FROM.finditer(code):
        for item in match.group(2).strip("()").split(","):
            parts = item.split()
            if parts:
                names[parts[-1]] = f"{match.group(1)}.{parts[0]}"
    for match in _PY_IMPORT.finditer(code):
        names[match.group(2) or match.group(1).split(".")[0]] = match.group(1)
    return names


def _django(route: str) -> str:
    route = route.lstrip("^").rstrip("$")
    return re.sub(r"\(\?P<\w+>[^)]*\)", "*", route)


# ---- JavaScript / TypeScript ---------------------------------------------------------------------

_JS_SERVER = re.compile(r"""(?:from\s+|require\(\s*)['"](express|fastify|koa|@koa/router|koa-router|hono|restify)['"]""")
_JS_ROUTE = re.compile(r"\b(\w+)\.(get|post|put|patch|delete|all|options)\(\s*(['\"`])(/[^'\"`]*)\3\s*,")
_JS_CLIENTS = {"axios", "http", "https", "ky", "got", "fetch", "superagent", "request", "$", "jquery", "api", "client",
               "apiclient", "instance", "service", "this", "httpclient", "$http", "supertest", "agent"}
_JS_MOUNT = re.compile(r"\.(?:use|register|route)\(\s*(['\"`])(/[^'\"`]*)\1\s*,\s*(?:[\w.]+\s*,\s*)*(\w+)\s*\)")
_JS_FASTIFY_MOUNT = re.compile(r"\.register\(\s*(\w+)\s*,\s*\{[^}]*prefix\s*:\s*(['\"`])(/[^'\"`]*)\2")
_JS_IMPORT = re.compile(r"""import\s+(\w+)\s*(?:,\s*\{[^}]*\})?\s+from\s+['"]([^'"]+)['"]|"""
                        r"""(?:const|let|var)\s+(\w+)\s*=\s*require\(\s*['"]([^'"]+)['"]\s*\)""")
_JS_NAMED_IMPORT = re.compile(r"""import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]""")
_JS_FETCH = re.compile(r"\bfetch\(\s*(['\"`])((?:[^'\"`\\]|\\.|\$\{(?:[^{}]|\{[^{}]*\})*\})*)\1")
_JS_CLIENT_CALL = re.compile(r"(?<![\w.])([\w$]+(?:\.[\w$]+)?)\.(get|post|put|patch|delete|head)\(\s*(['\"`])"
                             r"((?:[^'\"`\\]|\\.|\$\{(?:[^{}]|\{[^{}]*\})*\})*)\3")
_JS_AXIOS_CONFIG = re.compile(r"\b(?:axios|\$\.ajax|ajax)\(\s*\{([^}]*)\}")
_JS_JQUERY = re.compile(r"\$\.(get|post|getJSON)\(\s*(['\"`])([^'\"`]+)\2")
_JS_METHOD_OPT = re.compile(r"""\b(?:method|type)\s*:\s*['"`](\w+)['"`]""", re.I)
_JS_URL_OPT = re.compile(r"""\burl\s*:\s*(['"`])([^'"`]+)\1""")
_NEXT_APP_ROUTE = re.compile(r"(?:^|/)app/((?:[^/]+/)*)route\.[cm]?[jt]sx?$")
_NEXT_PAGES_API = re.compile(r"(?:^|/)pages/(api/(?:[^/]+/)*[^/]+)\.[cm]?[jt]sx?$")
_NEXT_HANDLER = re.compile(r"export\s+(?:async\s+)?(?:function|const)\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b")
_WP_AJAX_JS = re.compile(r"""\baction\s*[:=]\s*['"](\w+)['"]""")


def _rest_of_call(code: str, pos: int, limit: int = 600) -> str:
    """The remaining arguments of the call whose first argument ends at `pos` (up to its closing paren)."""
    depth = 1
    for i in range(pos, min(len(code), pos + limit)):
        if code[i] in "([{":
            depth += 1
        elif code[i] in ")]}":
            depth -= 1
            if depth == 0:
                return code[pos:i]
    return code[pos:pos + limit]


def _javascript(path: str, source: str) -> FileRoutes:
    out = FileRoutes()
    code = strip_comments(source)
    imports = _js_imports(code)
    server = bool(_JS_SERVER.search(code)) or bool(re.search(r"\b(?:express\.)?Router\(\)|new Hono\(", code))
    route_spans: List[Tuple[int, int]] = []
    if server:
        for match in _JS_ROUTE.finditer(code):
            obj = match.group(1)
            if obj.lower() in _JS_CLIENTS and obj not in ("app",):
                continue
            method = match.group(2).upper()
            handler = re.match(r"\s*(?:[\w.]+\s*,\s*)*([\w.]+)\s*\)", code[match.end():match.end() + 200])
            out.routes.append(Route("ANY" if method in ("ALL", "OPTIONS") else method, _join("", match.group(4)), path,
                                    _line(code, match.start()), handler.group(1) if handler else ""))
            route_spans.append((match.start(), match.end()))
        for match in _JS_MOUNT.finditer(code):
            module = imports.get(match.group(3))
            if module:
                out.mounts.append((match.group(2), module))
        for match in _JS_FASTIFY_MOUNT.finditer(code):
            module = imports.get(match.group(1))
            if module:
                out.mounts.append((match.group(3), module))
    _next_routes(out, path, code)
    for match in _JS_FETCH.finditer(code):
        method = _JS_METHOD_OPT.search(_rest_of_call(code, match.end()))
        _add_request(out, method.group(1).upper() if method else "GET", match.group(2), path, _line(code, match.start()))
    for match in _JS_CLIENT_CALL.finditer(code):
        if any(start <= match.start() < end for start, end in route_spans):
            continue
        obj = match.group(1).lower()
        if obj in ("app", "router", "server", "fastify", "map", "params", "searchparams", "headers", "cache", "store",
                   "localstorage", "sessionstorage", "formdata", "url", "weakmap", "cookies", "storage", "redis",
                   "db", "knex", "repo", "model", "config", "env", "process.env", "req", "res", "ctx", "c"):
            continue
        _add_request(out, match.group(2).upper(), match.group(4), path, _line(code, match.start()))
    for match in _JS_AXIOS_CONFIG.finditer(code):
        url = _JS_URL_OPT.search(match.group(1))
        method = _JS_METHOD_OPT.search(match.group(1))
        if url:
            _add_request(out, (method.group(1) if method else "GET").upper(), url.group(2), path, _line(code, match.start()))
    for match in _JS_JQUERY.finditer(code):
        _add_request(out, "POST" if match.group(1) == "post" else "GET", match.group(3), path, _line(code, match.start()))
    if re.search(r"admin-ajax|ajaxurl|ajax_url", code):
        for match in _WP_AJAX_JS.finditer(code):
            out.requests.append(Request("AJAX", f"/admin-ajax/{match.group(1)}", path, _line(code, match.start())))
    _collect_hosts(out, code)
    return out


def _js_imports(code: str) -> Dict[str, str]:
    names: Dict[str, str] = {}
    for match in _JS_IMPORT.finditer(code):
        name, spec = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
        names[name] = spec
    for match in _JS_NAMED_IMPORT.finditer(code):
        for item in match.group(1).split(","):
            parts = item.split()
            if parts:
                names[parts[-1]] = match.group(2)
    return names


def _next_routes(out: FileRoutes, path: str, code: str) -> None:
    app_route = _NEXT_APP_ROUTE.search(path)
    if app_route:
        segments = [s for s in app_route.group(1).split("/") if s and not (s.startswith("(") and s.endswith(")"))
                    and not s.startswith("@")]
        url = "/" + "/".join(segments)
        methods = sorted(set(_NEXT_HANDLER.findall(code))) or ["ANY"]
        for method in methods:
            out.routes.append(Route(method if method in METHODS else "ANY", _join("", url), path, 1, method))
        return
    pages = _NEXT_PAGES_API.search(path)
    if pages:
        url = "/" + pages.group(1)
        url = url[:-len("/index")] if url.endswith("/index") else url
        out.routes.append(Route("ANY", _join("", url), path, 1, "handler"))


# ---- PHP -----------------------------------------------------------------------------------------

_LARAVEL_ROUTE = re.compile(r"Route::(get|post|put|patch|delete|any|match)\(\s*(?:\[[^\]]*\]\s*,\s*)?['\"]([^'\"]*)['\"]\s*,\s*([^;]{0,160})")
_WP_REST = re.compile(r"register_rest_route\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]([^;]{0,600})", re.S)
_WP_REST_METHOD = re.compile(r"['\"]methods['\"]\s*=>\s*(?:['\"](\w+)['\"]|WP_REST_Server::(\w+))")
_WP_AJAX = re.compile(r"add_action\(\s*['\"]wp_ajax_(?:nopriv_)?(\w+)['\"]\s*,\s*([^;)]{0,120})")
_PHP_REQUEST = re.compile(r"\b(?:wp_remote_(get|post|request|head)|wp_safe_remote_(get|post|request)|curl_init|"
                          r"Http::(?:\w+\([^)]*\)->)*(get|post|put|patch|delete)|file_get_contents)\(\s*['\"]([^'\"]+)['\"]", re.I)
_WP_SERVER = {"READABLE": "GET", "CREATABLE": "POST", "EDITABLE": "PUT", "DELETABLE": "DELETE", "ALLMETHODS": "ANY"}


def _php(path: str, source: str) -> FileRoutes:
    out = FileRoutes()
    code = strip_comments(source, hash_comments=True)
    prefix = "/api" if re.search(r"(^|/)routes/api\.php$", path) else ""
    for match in _LARAVEL_ROUTE.finditer(code):
        method = "ANY" if match.group(1) in ("any", "match") else match.group(1).upper()
        out.routes.append(Route(method, _join(prefix, match.group(2)), path, _line(code, match.start()),
                                re.sub(r"\s+", " ", match.group(3)).strip(" )")[:80]))
    for match in _WP_REST.finditer(code):
        found = _WP_REST_METHOD.search(match.group(3))
        method = (found.group(1).upper() if found and found.group(1) else _WP_SERVER.get(found.group(2).upper(), "ANY")
                  if found else "GET")
        url = "/wp-json/" + match.group(1).strip("/") + "/" + _wp_route(match.group(2)).lstrip("/")
        out.routes.append(Route(method if method in METHODS else "ANY", _join("", url), path, _line(code, match.start())))
    for match in _WP_AJAX.finditer(code):
        out.routes.append(Route("AJAX", f"/admin-ajax/{match.group(1)}", path, _line(code, match.start()),
                                match.group(2).strip(" '\"")[:80]))
    for match in _PHP_REQUEST.finditer(code):
        verb = (match.group(1) or match.group(2) or match.group(3) or "get").upper()
        _add_request(out, "GET" if verb in ("REQUEST", "HEAD") else verb, match.group(4), path, _line(code, match.start()))
    _collect_hosts(out, code)
    return out


def _wp_route(route: str) -> str:
    return re.sub(r"\(\?P<\w+>[^)]*\)", "*", route)


# ---- shared --------------------------------------------------------------------------------------

_URL_LITERAL = re.compile(r"""['"`](https?://[a-zA-Z0-9.-]+)""")


def _collect_hosts(out: FileRoutes, code: str) -> None:
    for match in _URL_LITERAL.finditer(code):
        host = _host(match.group(1))
        if host:
            out.hosts.add(host)


def _add_request(out: FileRoutes, method: str, url: str, path: str, line: int) -> None:
    url = _template(url.strip())
    if not url or url.startswith(("data:", "blob:", "mailto:", "#")) or (not url.startswith(("/", "*", "http")) and "/" not in url):
        return
    host = _host(url)
    if url.startswith("http") and not host:
        return
    out.requests.append(Request(method if method in METHODS else "GET", url, path, line, host))
    if host:
        out.hosts.add(host)


def _join(prefix: str, route: str) -> str:
    joined = "/" + "/".join(p for p in (prefix.strip("/"), route.strip("/")) if p)
    return re.sub(r"/+", "/", joined)


def extract(path: str, language: str, source: str) -> FileRoutes:
    if language == "Python":
        return _python(path, source)
    if language in ("JavaScript", "TypeScript", "Vue", "Svelte"):
        return _javascript(path, source)
    if language == "PHP":
        return _php(path, source)
    return FileRoutes()


# ---- mounts and matching -----------------------------------------------------------------------

def apply_mounts(found: Dict[str, FileRoutes], uses: Dict[str, Set[str]]) -> None:
    """Prefix the routes of router files mounted from another file (app.use('/api', router),
    include_router(router, prefix=...), register_blueprint(bp, url_prefix=...)). The mounted file is
    the one whose path ends like the import, preferring files the mounting file is known to use;
    mounts inside mounts are applied from the top down, and each file is prefixed once."""
    every = list(found)
    mounted: Dict[str, Tuple[str, str]] = {}  # router file -> (prefix, mounting file)
    for path, fr in found.items():
        for prefix, spec in fr.mounts:
            target = _resolve(spec, uses.get(path, set())) or _resolve(spec, every)
            if target and target != path and target not in mounted:
                mounted[target] = (prefix, path)

    def full_prefix(path: str, seen: Set[str]) -> str:
        if path not in mounted or path in seen:
            return ""
        prefix, parent = mounted[path]
        return _join(full_prefix(parent, seen | {path}), prefix)

    for path in mounted:
        prefix = full_prefix(path, set())
        for route in found[path].routes if path in found else []:
            route.path = _join(prefix, route.path)


def _resolve(spec: str, candidates: Iterable[str]) -> Optional[str]:
    """The file an import specifier names (`./routes/users`, `app.routers.items`), if one fits."""
    tail = [p for p in re.split(r"[./\\]", spec) if p and p != "@"]
    if not tail:
        return None
    best: Optional[Tuple[int, int, str]] = None
    candidates = list(candidates)
    for path in candidates:
        parts = [p for p in re.sub(r"\.[^./]+$", "", path).split("/") if p]
        if parts and parts[-1] in ("index", "__init__"):
            parts = parts[:-1]
        if not parts or parts[-1] != tail[-1]:
            continue
        common = 0
        while common < min(len(parts), len(tail)) and parts[-1 - common] == tail[-1 - common]:
            common += 1
        score = (common, -len(path), path)
        best = score if best is None or score > best else best
    if best is None and len(tail) > 1:  # `from app.routers.items import router` names the router, not the file
        return _resolve(".".join(tail[:-1]), candidates)
    return best[2] if best else None


def _segments(path: str) -> List[str]:
    out = []
    for seg in path.strip("/").split("/"):
        if not seg:
            continue
        if seg == "*" or seg.startswith(":") or (seg.startswith("{") and seg.endswith("}")) or \
                (seg.startswith("<") and seg.endswith(">")) or (seg.startswith("[") and seg.endswith("]")) or "*" in seg:
            out.append("*")
        else:
            out.append(seg.lower())
    return out


def _fits(a: List[str], b: List[str]) -> bool:
    return len(a) == len(b) and all(x == y or x == "*" or y == "*" for x, y in zip(a, b))


def match(requests: List[Request], routes: List[Route]) -> List[Tuple[Request, Route, str]]:
    """(request, route, 'exact'|'suffix') for each request that reaches a route in this codebase."""
    shapes = [(r, _segments(r.path)) for r in routes]
    out: List[Tuple[Request, Route, str]] = []
    for req in requests:
        if req.host:
            continue  # a full URL goes to an outside host (or a deployed copy; the AI can add that edge)
        segs = _segments(_path_of(req.url))
        while segs and segs[0] == "*":  # an unknown base (`${API}/orders`) is dropped
            segs = segs[1:]
        if not segs:
            continue
        same_method = [(r, s) for r, s in shapes
                       if req.method == r.method or (r.method == "ANY" and req.method != "AJAX")]
        exact = [r for r, s in same_method if _fits(segs, s)]
        if exact:
            out += [(req, r, "exact") for r in exact[:3]]
            continue
        suffix = [r for r, s in same_method if len(s) > len(segs) and _fits(segs, s[-len(segs):])]
        if len(suffix) == 1:
            out.append((req, suffix[0], "suffix"))
    return out
