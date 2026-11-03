"""Scan a codebase for the map: files and their size, what each defines (with its doc comment), the
import links (the impact map's), outside packages and hosts, endpoints, web requests and which
request reaches which endpoint. Read-only and offline; nothing from the codebase is run.

`summary(scan)` is the short text the Codebase Cartographer starts from, and `worksheet(...)` the
digest of one part's files it names and describes from.
"""
from __future__ import annotations

import ast
import hashlib
import posixpath
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.platform.codebase_health.inventory import build_inventory
from app.platform.codebase_health.scanners import scan_secrets
from app.platform.codebase_map.routes import Request, Route, apply_mounts, extract, match
from app.platform.impact_map import build_map

MAPPED_LANGUAGES_SKIP = {"CSS"}  # styling files would only crowd the map
ENTRY = re.compile(r"(^|/)(main|index|app|server|manage|wsgi|asgi|functions|artisan|cli|__main__|"
                   r"page|layout|_app|App)\.[a-z]+$")


@dataclass
class FileInfo:
    path: str
    language: str
    lines: int
    sha: str = ""  # content fingerprint: an unchanged file keeps its description
    signature: str = ""  # what it defines and serves: a changed body alone doesn't need a new description
    doc: str = ""
    defines: List[str] = field(default_factory=list)


@dataclass
class Scan:
    root: str
    files: Dict[str, FileInfo] = field(default_factory=dict)
    uses: Dict[str, Set[str]] = field(default_factory=dict)  # file -> files it uses
    used_by: Dict[str, Set[str]] = field(default_factory=dict)
    packages: Dict[str, Set[str]] = field(default_factory=dict)  # outside package -> files using it
    hosts: Dict[str, Set[str]] = field(default_factory=dict)  # outside host -> files calling it
    routes: List[Route] = field(default_factory=list)
    requests: List[Request] = field(default_factory=list)
    http: List[Tuple[Request, Route, str]] = field(default_factory=list)
    stack: Dict[str, List[str]] = field(default_factory=dict)
    secrets: List[Dict[str, object]] = field(default_factory=list)  # file, line, kind (never the value)
    truncated: bool = False

    def entrypoints(self) -> List[str]:
        served = {r.file for r in self.routes}
        return sorted(p for p in self.files if (ENTRY.search(p) or p in served) and not self.used_by.get(p))[:40]


def build_scan(root: str) -> Scan:
    inv = build_inventory(Path(root))
    imap = build_map(root, inventory=inv)
    scan = Scan(root=str(inv.root), stack=inv.stack, truncated=imap.truncated,
                secrets=scan_secrets(inv)[0]["locations"])
    found = {}
    for item in inv.files:
        if item.path not in imap.files or item.language in MAPPED_LANGUAGES_SKIP:
            continue
        source = inv.read(item.path) or ""
        language = imap.files[item.path]
        doc, defines = digest(item.path, language, source)
        info = FileInfo(item.path, language, item.lines, hashlib.sha1(source.encode("utf-8", "replace")).hexdigest()[:16],
                        doc=doc, defines=defines)
        scan.files[item.path] = info
        found[item.path] = extract(item.path, language, source)
    for user, used in imap.uses.items():
        if user in scan.files:
            scan.uses[user] = {u for u in used if u in scan.files}
    for user, used in scan.uses.items():
        for u in used:
            scan.used_by.setdefault(u, set()).add(user)
    scan.packages = {name: {p for p in paths if p in scan.files} for name, paths in imap.packages.items()}
    apply_mounts(found, scan.uses)
    for path, fr in found.items():
        scan.routes += fr.routes
        scan.requests += fr.requests
        for host in fr.hosts:
            scan.hosts.setdefault(host, set()).add(path)
    scan.http = match(scan.requests, scan.routes)
    serves: Dict[str, List[str]] = {}
    for r in scan.routes:
        serves.setdefault(r.file, []).append(r.key)
    for path, info in scan.files.items():
        info.signature = hashlib.sha1("|".join(info.defines + sorted(serves.get(path, [])) + [info.doc])
                                      .encode()).hexdigest()[:16]
    return scan


# ---- what each file defines ----------------------------------------------------------------------

_JS_EXPORT = re.compile(r"export\s+(?:default\s+)?(?:async\s+)?(?:function\*?|class|const|let|var|interface|type|enum)\s+(\w+)")
_JS_LEAD_COMMENT = re.compile(r"\A\s*(?:'use \w+';?\s*)?(?:/\*\*?(.*?)\*/|((?://[^\n]*\n\s*)+))", re.S)
_PHP_DOC = re.compile(r"<\?php\s*(?:/\*\*?(.*?)\*/)", re.S)
_PHP_HEADER = re.compile(r"^\s*\*?\s*(Plugin Name|Template Name|Theme Name|Description):\s*(.+)$", re.M)
_PHP_DEFS = re.compile(r"\b(?:class|interface|trait|function)\s+([A-Za-z_]\w*)")
_GENERIC_COMMENT = re.compile(r"\A\s*(?:#!.*\n)?\s*(?:#|//|--)\s*(.+)")


def _first_sentence(text: str) -> str:
    text = re.sub(r"^\s*[*#/]+\s?", "", text or "", flags=re.M)
    text = re.sub(r"@\w+.*", "", text)
    text = " ".join(text.split())
    return text[:240]


def digest(path: str, language: str, source: str) -> Tuple[str, List[str]]:
    """(doc comment, names it defines with their own one-line doc) for the worksheet."""
    if language == "Python":
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            return "", []
        defines = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
                doc = _first_sentence((ast.get_docstring(node) or "").split("\n\n")[0])
                defines.append(f"{node.name}: {doc[:120]}" if doc else node.name)
        return _first_sentence((ast.get_docstring(tree) or "").split("\n\n")[0]), defines[:15]
    if language in ("JavaScript", "TypeScript", "Vue", "Svelte"):
        lead = _JS_LEAD_COMMENT.match(source)
        doc = _first_sentence((lead.group(1) or lead.group(2)) if lead else "")
        return doc, list(dict.fromkeys(_JS_EXPORT.findall(source)))[:15]
    if language == "PHP":
        header = _PHP_HEADER.findall(source[:3000])
        lead = _PHP_DOC.match(source)
        doc = "; ".join(f"{k}: {v.strip()}" for k, v in header[:2]) or _first_sentence(lead.group(1) if lead else "")
        return doc[:240], list(dict.fromkeys(_PHP_DEFS.findall(source)))[:15]
    comment = _GENERIC_COMMENT.match(source)
    return (comment.group(1).strip()[:200] if comment else ""), []


# ---- what the Cartographer reads ----------------------------------------------------------------

def _dir(path: str, depth: int) -> str:
    parts = path.split("/")[:-1]
    return "/".join(parts[:depth]) or "."


def summary(scan: Scan, limit: int = 14000) -> str:
    total = sum(f.lines for f in scan.files.values())
    stack = ", ".join(f"{k}: {', '.join(v)}" for k, v in scan.stack.items() if v) or "unknown"
    lines = [f"FILES {len(scan.files)} ({total:,} lines){' (truncated)' if scan.truncated else ''}; stack: {stack}", "",
             "TREE (folder: files, lines)"]
    dirs: Dict[str, List[int]] = {}
    for f in scan.files.values():
        for depth in (1, 2, 3):
            d = _dir(f.path, depth)
            if depth > 1 and d == _dir(f.path, depth - 1):
                continue
            entry = dirs.setdefault(d, [0, 0])
            entry[0] += 1
            entry[1] += f.lines
    for d, (count, loc) in sorted(dirs.items())[:90]:
        lines.append(f"  {d}/: {count} files, {loc:,} lines")
    lines += ["", "ENTRY POINTS", *[f"  {p}" for p in scan.entrypoints()[:25]]]
    links: Counter = Counter()
    for user, used in scan.uses.items():
        for u in used:
            a, b = _dir(user, 2), _dir(u, 2)
            if a != b:
                links[(a, b)] += 1
    lines += ["", "HEAVIEST FOLDER -> FOLDER IMPORTS", *[f"  {a} -> {b}: {n}" for (a, b), n in links.most_common(25)]]
    lines += ["", f"ENDPOINTS ({len(scan.routes)})", *[f"  {r.key}  ({r.file}:{r.line})" for r in scan.routes[:60]]]
    if len(scan.routes) > 60:
        lines.append(f"  … and {len(scan.routes) - 60} more")
    pairs = Counter((req.file, route.file) for req, route, _ in scan.http)
    lines += ["", f"WEB REQUESTS MATCHED TO ENDPOINTS ({len(scan.http)})",
              *[f"  {a} -> {b}: {n} request(s)" for (a, b), n in pairs.most_common(30)]]
    matched = {id(q) for q, _, _ in scan.http}
    unmatched = [r for r in scan.requests if not r.host and id(r) not in matched]
    if unmatched:
        lines += [f"UNMATCHED REQUESTS ({len(unmatched)})", *[f"  {r.method} {r.url}  ({r.file})" for r in unmatched[:15]]]
    top_packages = sorted(scan.packages.items(), key=lambda kv: -len(kv[1]))[:35]
    lines += ["", "OUTSIDE PACKAGES (used by N files)", *[f"  {name}: {len(paths)}" for name, paths in top_packages]]
    lines += ["", "OUTSIDE HOSTS CALLED", *[f"  {h}: {', '.join(sorted(p)[:3])}" for h, p in sorted(scan.hosts.items())[:30]]]
    text = "\n".join(lines)
    return text if len(text) <= limit else text[:limit] + "\n… (cut short)"


def worksheet(scan: Scan, paths: List[str], route_keys: List[str]) -> str:
    """Everything needed to name and describe these files and endpoints without opening them."""
    by_key = {r.key: r for r in scan.routes}
    out = []
    for path in paths:
        f = scan.files[path]
        uses = sorted(scan.uses.get(path, ()))[:6]
        used_by = sorted(scan.used_by.get(path, ()))[:6]
        packages = sorted(n for n, ps in scan.packages.items() if path in ps)[:6]
        out.append(f"### {path}  ({f.language}, {f.lines} lines)")
        if f.doc:
            out.append(f"doc: {f.doc}")
        if f.defines:
            out.append("defines: " + "; ".join(f.defines))
        if uses:
            out.append("uses: " + ", ".join(uses))
        if used_by:
            out.append("used by: " + ", ".join(used_by))
        if packages:
            out.append("packages: " + ", ".join(packages))
    if route_keys:
        out.append("\n## Endpoints")
        for key in route_keys:
            r = by_key.get(key)
            if r:
                callers = sorted({req.file for req, route, _ in scan.http if route.key == key})[:4]
                out.append(f"- {key}  (in {r.file}:{r.line}{', handler ' + r.handler if r.handler else ''})"
                           + (f"; called from {', '.join(callers)}" if callers else ""))
    return "\n".join(out)


def route_owner(scan: Scan) -> Dict[str, str]:
    return {r.key: r.file for r in scan.routes}


def unique_routes(scan: Scan) -> List[Route]:
    seen: Dict[str, Route] = {}
    for r in scan.routes:
        seen.setdefault(r.key, r)
    return list(seen.values())


def normalise(path: str) -> Optional[str]:
    clean = posixpath.normpath(str(path or "").replace("\\", "/").lstrip("/"))
    return None if not clean or clean.startswith("..") or clean == "." else clean
