"""Turn the scan plus the Codebase Cartographer's architecture and descriptions into the map.

- `check_architecture` names every problem in the architecture (unknown parents, bad kinds, steps
  pointing nowhere, too much code unassigned) so the Cartographer can fix it.
- `assign` gives every file to exactly one part: the deepest part whose `paths` globs match and
  whose `exclude` globs (its own and its ancestors') don't; between equally deep parts the glob with
  the longer literal prefix wins. Files nobody claims go to "Unassigned".
- `build_graph` produces what the viewer draws: parts, files and endpoints with plain names and
  descriptions, file-level links (imports, web requests matched to endpoints, outside packages and
  hosts), the Cartographer's extra connections, guided flows, the "Start here" tour and Health.
"""
from __future__ import annotations

import fnmatch
import posixpath
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.platform.codebase_map.scan import Scan, unique_routes

KINDS = ("ui", "service", "worker", "library", "feature", "data", "config", "test", "script", "infra", "external")
EDGE_KINDS = ("import", "call", "http", "rpc", "event", "queue", "data", "config")
NODE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
UNASSIGNED = "_unassigned"
MAX_UNASSIGNED = 0.10
BIG_FILE_LINES = 1000
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]+\.py$|[._-](test|spec)\.[a-z]+$", re.I)
CONFIG_PATH = re.compile(r"(^|/)[\w.-]*\.config\.[cm]?[jt]s$|(^|/)(setup|conftest|manage|settings|config|wsgi|asgi|"
                         r"__init__|__main__)\.py$|(^|/)\.", re.I)


# ---- globs -------------------------------------------------------------------------------------

def _glob_regex(pattern: str) -> str:
    out, i, n = [], 0, len(pattern)
    while i < n:
        ch = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        elif ch == "{":
            end = pattern.find("}", i)
            if end < 0:
                out.append(re.escape(ch))
                i += 1
                continue
            out.append("(?:" + "|".join(_glob_regex(p) for p in pattern[i + 1:end].split(",")) + ")")
            i = end + 1
        elif ch == "[":
            # a whole folder name in brackets ([id], [...slug], [[...slug]]) is literal (Next.js, SvelteKit)
            whole = re.match(r"\[\[?\.{0,3}[\w-]+\]\]?(?=/|$)", pattern[i:])
            if whole and (i == 0 or pattern[i - 1] == "/"):
                out.append(re.escape(whole.group(0)))
                i += len(whole.group(0))
                continue
            end = pattern.find("]", i)
            if end < 0:
                out.append(re.escape(ch))
                i += 1
                continue
            out.append("[" + pattern[i + 1:end].replace("\\", "\\\\") + "]")
            i = end + 1
        else:
            out.append(re.escape(ch))
            i += 1
    return "".join(out)


class Glob:
    def __init__(self, pattern: str) -> None:
        pattern = pattern.strip().lstrip("./").rstrip("/")
        self.pattern = pattern
        self.prefix = len(re.split(r"[*?{\[]", pattern, 1)[0])
        plain = not re.search(r"[*?{]", pattern) and not re.search(r"\[[^\]]*\](?!/|$)", pattern)
        body = _glob_regex(pattern)
        # a pattern with no wildcard also matches as a folder: `backend/app` == `backend/app/**`
        self.regex = re.compile(f"^{body}(?:/.*)?$" if plain else f"^{body}$")

    def matches(self, path: str) -> bool:
        return bool(self.regex.match(path))


# ---- the architecture ----------------------------------------------------------------------------

def _str(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _list(value: Any, limit: int = 40) -> List[str]:
    return [str(v).strip() for v in (value or []) if str(v).strip()][:limit] if isinstance(value, list) else []


def clean_architecture(raw: Dict[str, Any]) -> Dict[str, Any]:
    """The architecture with every field trimmed to the expected shape (nothing judged yet)."""
    project = raw.get("project") if isinstance(raw.get("project"), dict) else {}
    nodes = []
    for n in (raw.get("nodes") or [])[:80]:
        if not isinstance(n, dict):
            continue
        nodes.append({"id": _str(n.get("id"), 80), "label": _str(n.get("label"), 60) or _str(n.get("id"), 60),
                      "kind": _str(n.get("kind"), 20), "parent": _str(n.get("parent"), 80) or None,
                      "summary": _str(n.get("summary"), 400), "details": _str(n.get("details"), 1500),
                      "paths": _list(n.get("paths")), "exclude": _list(n.get("exclude")),
                      "packages": _list(n.get("packages")), "hosts": _list(n.get("hosts"))})
    ids = {n["id"] for n in nodes}
    for n in nodes:  # `web.orders` without a parent: models often name the hierarchy only in the id
        if not n["parent"] and "." in n["id"] and n["kind"] != "external":
            prefix = n["id"].rsplit(".", 1)[0]
            while prefix and prefix not in ids:
                prefix = prefix.rsplit(".", 1)[0] if "." in prefix else ""
            n["parent"] = prefix or None
    edges = [{"from": _str(e.get("from"), 300), "to": _str(e.get("to"), 300), "kind": _str(e.get("kind"), 20) or "call",
              "label": _str(e.get("label"), 80), "description": _str(e.get("description"), 400)}
             for e in (raw.get("edges") or [])[:60] if isinstance(e, dict)]
    flows = [{"id": _str(f.get("id"), 60) or f"flow-{i}", "title": _str(f.get("title"), 80),
              "description": _str(f.get("description"), 400),
              "steps": [{"ref": _str(s.get("node"), 300), "note": _str(s.get("note"), 300)}
                        for s in (f.get("steps") or [])[:12] if isinstance(s, dict)]}
             for i, f in enumerate((raw.get("flows") or [])[:8]) if isinstance(f, dict)]
    tour = [{"ref": _str(s.get("node"), 300), "title": _str(s.get("title"), 80), "note": _str(s.get("note"), 400)}
            for s in (raw.get("tour") or [])[:8] if isinstance(s, dict)]
    return {"project": {"name": _str(project.get("name"), 80), "summary": _str(project.get("summary"), 800)},
            "audience": "developers" if raw.get("audience") == "developers" else "everyone",
            "nodes": nodes, "edges": edges, "flows": flows, "tour": tour}


def _ancestors(nodes: Dict[str, Dict[str, Any]], node_id: str) -> List[str]:
    out, seen = [], set()
    current = nodes.get(node_id, {}).get("parent")
    while current and current in nodes and current not in seen:
        out.append(current)
        seen.add(current)
        current = nodes[current].get("parent")
    return out


def assign(scan: Scan, arch: Dict[str, Any]) -> Dict[str, str]:
    """file -> part id (UNASSIGNED when nobody claims it)."""
    nodes = {n["id"]: n for n in arch["nodes"]}
    compiled = []
    for n in arch["nodes"]:
        if n["kind"] == "external" or not n["paths"]:
            continue
        excludes = [Glob(p) for a in [n["id"], *_ancestors(nodes, n["id"])] for p in nodes[a]["exclude"]]
        compiled.append((n["id"], len(_ancestors(nodes, n["id"])), [Glob(p) for p in n["paths"]], excludes))
    owner: Dict[str, str] = {}
    for path in scan.files:
        best: Optional[Tuple[int, int, str]] = None
        for node_id, depth, globs, excludes in compiled:
            hits = [g.prefix for g in globs if g.matches(path)]
            if not hits or any(x.matches(path) for x in excludes):
                continue
            score = (depth, max(hits), node_id)
            if best is None or score[:2] > best[:2]:
                best = score
        owner[path] = best[2] if best else UNASSIGNED
    return owner


def _resolve_ref(ref: str, nodes: Dict[str, Any], scan: Scan, routes: Set[str]) -> Optional[str]:
    if ref in nodes or ref in scan.files or ref in routes:
        return ref
    clean = posixpath.normpath(ref.replace("\\", "/").lstrip("./")) if ref else ""
    return clean if clean in scan.files else None


def check_architecture(scan: Scan, arch: Dict[str, Any]) -> List[str]:
    """Problems to send back to the Cartographer, each named precisely."""
    problems: List[str] = []
    if not arch["project"]["name"]:
        problems.append("project.name is missing.")
    nodes: Dict[str, Dict[str, Any]] = {}
    for n in arch["nodes"]:
        if not NODE_ID.match(n["id"]):
            problems.append(f"Node id {n['id']!r} may only use letters, digits, '_', '-' and '.'.")
        elif n["id"] in nodes:
            problems.append(f"Node id {n['id']!r} is used twice.")
        nodes[n["id"]] = n
    if not nodes:
        return problems + ["There are no nodes."]
    for n in arch["nodes"]:
        if n["kind"] not in KINDS:
            problems.append(f"Node {n['id']!r} has kind {n['kind']!r}; use one of {', '.join(KINDS)}.")
        if n["parent"] and n["parent"] not in nodes:
            problems.append(f"Node {n['id']!r} has parent {n['parent']!r}, which isn't a node.")
        if n["id"] in _ancestors(nodes, n["id"]):
            problems.append(f"Node {n['id']!r} is its own ancestor.")
        if not n["summary"]:
            problems.append(f"Node {n['id']!r} needs a summary.")
        if n["kind"] == "external" and n["paths"]:
            problems.append(f"External node {n['id']!r} can't claim files; use packages or hosts.")
    routes = {r.key for r in scan.routes}
    for e in arch["edges"]:
        for end in ("from", "to"):
            if not _resolve_ref(e[end], nodes, scan, routes):
                problems.append(f"Edge {e['from']} -> {e['to']}: {e[end]!r} is not a node id or file path.")
    for f in arch["flows"]:
        if len(f["steps"]) < 2:
            problems.append(f"Flow {f['id']!r} needs at least 2 steps.")
        for s in f["steps"]:
            if not _resolve_ref(s["ref"], nodes, scan, routes):
                problems.append(f"Flow {f['id']!r}: step {s['ref']!r} is not a node id or file path.")
    for s in arch["tour"]:
        if not _resolve_ref(s["ref"], nodes, scan, routes):
            problems.append(f"Tour stop {s['ref']!r} is not a node id or file path.")
    if scan.files:
        owner = assign(scan, arch)
        loose = [p for p, o in owner.items() if o == UNASSIGNED]
        if len(loose) > MAX_UNASSIGNED * len(scan.files):
            by_dir: Dict[str, int] = {}
            for p in loose:
                d = posixpath.dirname(p) or "(top level)"
                by_dir[d] = by_dir.get(d, 0) + 1
            top = ", ".join(f"{d} ({n})" for d, n in sorted(by_dir.items(), key=lambda kv: -kv[1])[:8])
            problems.append(f"{len(loose)} of {len(scan.files)} files belong to no node (keep it under "
                            f"{int(MAX_UNASSIGNED * 100)}%). Unclaimed files by folder: {top}.")
        claimed = set(owner.values())
        for n in arch["nodes"]:
            if n["kind"] != "external" and n["paths"] and n["id"] not in claimed and \
                    not any(c for c in claimed if n["id"] in _ancestors(nodes, c)):
                problems.append(f"Node {n['id']!r} claims no files (paths {', '.join(n['paths'][:3])}).")
    return problems[:40]


def drop_invalid(scan: Scan, arch: Dict[str, Any]) -> Dict[str, Any]:
    """What's left once anything still broken after the Cartographer's fixes is removed."""
    nodes: Dict[str, Dict[str, Any]] = {}
    for n in arch["nodes"]:
        if NODE_ID.match(n["id"]) and n["id"] not in nodes:
            nodes[n["id"]] = {**n, "kind": n["kind"] if n["kind"] in KINDS else "feature"}
    for n in nodes.values():
        if n["parent"] not in nodes or n["id"] in _ancestors(nodes, n["id"]):
            n["parent"] = None
        if n["kind"] == "external":
            n["paths"] = []
    routes = {r.key for r in scan.routes}
    ok = lambda ref: _resolve_ref(ref, nodes, scan, routes)  # noqa: E731
    edges = [{**e, "from": ok(e["from"]), "to": ok(e["to"]), "kind": e["kind"] if e["kind"] in EDGE_KINDS else "call"}
             for e in arch["edges"] if ok(e["from"]) and ok(e["to"])]
    flows = []
    for f in arch["flows"]:
        steps = [{**s, "ref": ok(s["ref"])} for s in f["steps"] if ok(s["ref"])]
        if len(steps) >= 2:
            flows.append({**f, "steps": steps})
    tour = [{**s, "ref": ok(s["ref"])} for s in arch["tour"] if ok(s["ref"])]
    return {**arch, "nodes": list(nodes.values()), "edges": edges, "flows": flows, "tour": tour}


# ---- outside services ----------------------------------------------------------------------------

def _package_matches(pattern: str, package: str) -> bool:
    pattern = re.sub(r"^(npm|pypi|composer|go|gem|cargo|maven):", "", pattern.strip())
    return fnmatch.fnmatchcase(package.lower(), pattern.lower())


def _host_matches(pattern: str, host: str) -> bool:
    pattern = pattern.strip().lower()
    return fnmatch.fnmatchcase(host, pattern) or host.endswith("." + pattern.lstrip("*."))


# ---- health ------------------------------------------------------------------------------------

def health(scan: Scan, entrypoints: Set[str]) -> List[Dict[str, Any]]:
    """Plain-language problems the scan can see, each pointing at files (never a secret's value)."""
    items: List[Dict[str, Any]] = []
    if scan.secrets:
        items.append({"id": "secrets", "severity": "high", "title": "Passwords or keys written into the code",
                      "detail": "Anyone who can see the code can copy these. Move them to settings outside the code "
                                "and replace (rotate) them.",
                      "refs": [{"ref": s["file"], "note": f"{s['kind']}" + (f" (line {s['line']})" if s.get("line") else "")}
                               for s in scan.secrets[:30] if s["file"] in scan.files]})
    big = sorted((f for f in scan.files.values() if f.lines > BIG_FILE_LINES), key=lambda f: -f.lines)
    if big:
        items.append({"id": "big-files", "severity": "medium", "title": "Very long files",
                      "detail": f"Files over {BIG_FILE_LINES:,} lines are hard to change safely, by people and by AI.",
                      "refs": [{"ref": f.path, "note": f"{f.lines:,} lines"} for f in big[:20]]})
    root = Path(scan.root)

    def in_js_project(path: str) -> bool:  # outside a package.json project, scripts are loaded by pages, not imports
        parts = path.split("/")[:-1]
        return any((root.joinpath(*parts[:i]) / "package.json").is_file() for i in range(len(parts), -1, -1))

    unused = sorted(p for p, f in scan.files.items()
                    if (f.language == "Python" or f.language in ("JavaScript", "TypeScript", "Vue", "Svelte") and in_js_project(p))
                    and not scan.used_by.get(p)
                    and p not in entrypoints and not TEST_PATH.search(p) and not CONFIG_PATH.search(p)
                    and not any(r.file == p for r in scan.routes))
    if unused:
        items.append({"id": "unused", "severity": "low", "title": "Files nothing seems to use",
                      "detail": "No other file imports these and they aren't entry points. They may be dead code, or "
                                "loaded in a way the scan can't see (check before deleting).",
                      "refs": [{"ref": p, "note": ""} for p in unused[:40]]})
    for item in items:
        item["count"] = len(item["refs"])
    return [i for i in items if i["refs"]]


# ---- the graph --------------------------------------------------------------------------------------

def build_graph(scan: Scan, arch: Dict[str, Any], descriptions: Dict[str, Dict[str, Dict[str, str]]]) -> Dict[str, Any]:
    owner = assign(scan, arch)
    nodes = [dict(n) for n in arch["nodes"]]
    if any(o == UNASSIGNED for o in owner.values()):
        nodes.append({"id": UNASSIGNED, "label": "Unassigned", "kind": "feature", "parent": None,
                      "summary": "Files the map couldn't place in a part.", "details": "", "paths": [], "exclude": [],
                      "packages": [], "hosts": []})
    by_id = {n["id"]: n for n in nodes}
    file_desc, route_desc = descriptions.get("files", {}), descriptions.get("routes", {})
    serves: Dict[str, List[str]] = {}
    for r in unique_routes(scan):
        serves.setdefault(r.file, []).append(r.key)
    files = []
    for path, f in sorted(scan.files.items()):
        d = file_desc.get(path) or {}
        files.append({"path": path, "node": owner[path], "name": d.get("name") or posixpath.basename(path),
                      "description": d.get("description") or f.doc, "lines": f.lines, "language": f.language,
                      "routes": serves.get(path, []), "sha": f.sha, "signature": f.signature,
                      "defines": [x.split(":")[0] for x in f.defines][:12]})
    routes = [{"key": r.key, "method": r.method, "path": r.path, "file": r.file, "line": r.line, "handler": r.handler,
               "name": (route_desc.get(r.key) or {}).get("name") or r.key,
               "description": (route_desc.get(r.key) or {}).get("description") or ""} for r in unique_routes(scan)]
    links: List[List[str]] = []
    for user, used in sorted(scan.uses.items()):
        links += [[user, u, "import", ""] for u in sorted(used)]
    seen_http: Set[Tuple[str, str, str]] = set()
    for req, route, _ in scan.http:
        if req.file != route.file and (req.file, route.file, route.key) not in seen_http:
            seen_http.add((req.file, route.file, route.key))
            links.append([req.file, route.file, "http", route.key])
    externals = [n for n in nodes if n["kind"] == "external"]
    for ext in externals:
        users: Set[str] = set()
        for package, paths in scan.packages.items():
            if any(_package_matches(p, package) for p in ext["packages"]):
                users |= paths
        for path in sorted(users):
            links.append([path, ext["id"], "package", ""])
        callers: Set[str] = set()
        for host, paths in scan.hosts.items():
            if any(_host_matches(h, host) for h in ext["hosts"]):
                callers |= paths
        for path in sorted(callers - users):
            links.append([path, ext["id"], "http", ""])
    for n in nodes:
        n["depth"] = len(_ancestors(by_id, n["id"]))
        n["file_count"] = sum(1 for o in owner.values() if o == n["id"] or n["id"] in _ancestors(by_id, o))
        n["line_count"] = sum(scan.files[p].lines for p, o in owner.items() if o == n["id"] or n["id"] in _ancestors(by_id, o))
        for key in ("paths", "exclude", "packages", "hosts"):
            n[key] = n.get(key) or []
    entry = set(scan.entrypoints())
    described = sum(1 for f in files if (file_desc.get(f["path"]) or {}).get("description"))
    return {
        "version": 1,
        "project": arch["project"], "audience": arch.get("audience", "everyone"),
        "nodes": nodes, "files": files, "routes": routes, "links": links, "edges": arch["edges"],
        "flows": arch["flows"], "tour": arch["tour"] or _default_tour(nodes, arch["flows"]),
        "health": health(scan, entry),
        "stats": {"files": len(files), "lines": sum(f["lines"] for f in files), "routes": len(routes),
                  "http_links": len(seen_http), "unassigned": sum(1 for o in owner.values() if o == UNASSIGNED),
                  "described": described, "truncated": scan.truncated},
    }


def _default_tour(nodes: List[Dict[str, Any]], flows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    top = [n for n in nodes if not n["parent"] and n["id"] != UNASSIGNED]
    order = sorted(top, key=lambda n: KINDS.index(n["kind"]) if n["kind"] in KINDS else 99)
    return [{"ref": n["id"], "title": n["label"], "note": n["summary"]} for n in order[:6]]
