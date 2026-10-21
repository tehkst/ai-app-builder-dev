"""The impact map: who depends on whom in a client codebase, and what a change would affect.

`build_map(root)` reads the codebase (the Health Check's inventory: git-tracked or walked files,
vendored and generated folders skipped, nothing executed) and links files:

    A -> B   means "A uses B", so changing B can break A.

`impact(map, target)` answers "what breaks if we change this?" for a file, a PHP class or function,
a WordPress hook or an outside package: the files that use it directly, everything that depends on
those in turn, the pages/entry points among them, and the tests that cover any of it.
"""
from __future__ import annotations

import json
import posixpath
import re
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from app.platform.codebase_health.inventory import Inventory, build_inventory
from app.platform.impact_map.parsers import FileFacts, parse

JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".json")
SFC_LANGUAGES = {".vue": "Vue", ".svelte": "Svelte"}
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]+\.py$|[._-](test|spec)\.[a-z]+$|Test\.php$", re.I)
WP_ENTRY = re.compile(r"(^|/)(index|functions|header|footer|sidebar|page(-[\w-]+)?|single(-[\w-]+)?|archive(-[\w-]+)?|"
                      r"category|tag|taxonomy|author|search|404|front-page|home|comments)\.php$")
CONFIG_FILE = re.compile(r"(^|/)[\w.-]*\.config\.[cm]?[jt]s$|(^|/)(gulpfile|gruntfile|webpack\.[\w.]+)\.js$", re.I)
MAX_FILES = 20_000
NODE_BUILTINS = {"assert", "buffer", "child_process", "cluster", "crypto", "dgram", "dns", "events", "fs", "http", "http2",
                 "https", "net", "os", "path", "perf_hooks", "process", "querystring", "readline", "stream", "string_decoder",
                 "timers", "tls", "tty", "url", "util", "v8", "vm", "worker_threads", "zlib"}
PYTHON_STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
WIDE_IMPACT_FILES = 10


@dataclass
class ImpactMap:
    root: str
    files: Dict[str, str] = field(default_factory=dict)  # path -> language
    uses: Dict[str, Set[str]] = field(default_factory=dict)  # path -> paths it uses
    used_by: Dict[str, Set[str]] = field(default_factory=dict)  # path -> paths that use it
    kinds: Dict[Tuple[str, str], Set[str]] = field(default_factory=dict)  # (user, used) -> link kinds
    packages: Dict[str, Set[str]] = field(default_factory=dict)  # outside package -> paths using it
    classes: Dict[str, str] = field(default_factory=dict)  # PHP class FQN -> defining path
    functions: Dict[str, str] = field(default_factory=dict)  # PHP global function -> defining path
    hooks: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)  # hook -> {"added": paths, "fired": paths}
    unresolved: int = 0
    truncated: bool = False

    def link(self, user: str, used: str, kind: str) -> None:
        if user == used:
            return
        self.uses.setdefault(user, set()).add(used)
        self.used_by.setdefault(used, set()).add(user)
        self.kinds.setdefault((user, used), set()).add(kind)

    @property
    def link_count(self) -> int:
        return sum(len(v) for v in self.uses.values())

    def is_test(self, path: str) -> bool:
        return bool(TEST_PATH.search(path))

    def entry_points(self) -> Set[str]:
        """Files nothing else in the project uses (pages, scripts, app entries), plus WordPress
        templates and PHP files under public/ - the places a visitor or a command lands first."""
        found = set()
        for path, language in self.files.items():
            if self.is_test(path) or CONFIG_FILE.search(path) or language not in ("PHP", "JavaScript", "TypeScript", "Python", "Vue", "Svelte"):
                continue
            if not self.used_by.get(path) or (language == "PHP" and (WP_ENTRY.search(path) or path.startswith(("public/", "web/")))):
                found.add(path)
        return found


# ---- building -----------------------------------------------------------------------------------------

def build_map(root: str, inventory: Optional[Inventory] = None) -> ImpactMap:
    inv = inventory or build_inventory(Path(root))
    imap = ImpactMap(root=str(inv.root))
    facts: Dict[str, FileFacts] = {}
    for item in inv.files:
        if len(imap.files) >= MAX_FILES:
            imap.truncated = True
            break
        language = SFC_LANGUAGES.get(Path(item.path).suffix.lower(), item.language)
        parsed = None
        if language in ("PHP", "JavaScript", "TypeScript", "Vue", "Svelte", "Python"):
            source = inv.read(item.path)
            parsed = parse(source, language) if source is not None else None
        imap.files[item.path] = language
        if parsed:
            facts[item.path] = parsed
    by_suffix = _suffix_index(imap.files)
    _php_symbols(imap, facts)
    js_aliases = _js_aliases(inv)
    composer = _composer_packages(inv)
    for path, f in facts.items():
        imap.unresolved += f.unresolved
        if f.language == "PHP":
            _link_php(imap, path, f, by_suffix, composer)
        elif f.language == "Python":
            _link_python(imap, path, f)
        else:
            _link_js(imap, path, f, js_aliases)
    for hook, sides in imap.hooks.items():  # firing a hook runs every handler added for it
        for firer in sides.get("fired", ()):
            for handler in sides.get("added", ()):
                imap.link(firer, handler, f"hook:{hook}")
    return imap


def _suffix_index(files: Iterable[str]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for path in files:
        parts = path.split("/")
        for i in range(len(parts)):
            index.setdefault("/".join(parts[i:]), []).append(path)
    return index


def _php_symbols(imap: ImpactMap, facts: Dict[str, FileFacts]) -> None:
    for path, f in facts.items():
        if f.language != "PHP":
            continue
        for fqn in f.classes:
            imap.classes.setdefault(fqn, path)
        for name in f.functions:
            imap.functions.setdefault(name, path)
        for hook in f.hooks_added:
            imap.hooks.setdefault(hook, {}).setdefault("added", set()).add(path)
        for hook in f.hooks_fired:
            imap.hooks.setdefault(hook, {}).setdefault("fired", set()).add(path)


def _resolve_include(path: str, literal: str, by_suffix: Dict[str, List[str]], files: Dict[str, str]) -> Optional[str]:
    clean = literal.replace("\\", "/")
    if not clean.startswith("/"):
        candidate = posixpath.normpath(posixpath.join(posixpath.dirname(path), clean))
        if candidate in files:
            return candidate
    hits = by_suffix.get(clean.lstrip("/").removeprefix("./"))
    if hits and len(hits) == 1:
        return hits[0]
    if hits:  # several files end like that: prefer the one nearest the including file
        return min(hits, key=lambda h: len(posixpath.relpath(h, posixpath.dirname(path) or ".")))
    return None


def _resolve_class(name: str, f: FileFacts, imap: ImpactMap, short_index: Dict[str, List[str]]) -> Optional[str]:
    aliases = {alias.lower(): fqn for alias, fqn in f.uses}
    head, _, rest = name.partition("\\")
    if head.lower() in aliases:
        fqn = aliases[head.lower()] + ("\\" + rest if rest else "")
    elif "\\" in name or not f.namespace:
        fqn = name
    else:
        fqn = f.namespace + "\\" + name
    if fqn in imap.classes:
        return imap.classes[fqn]
    hits = short_index.get(name.rsplit("\\", 1)[-1].lower(), [])
    return hits[0] if len(hits) == 1 else None  # unique short name only: never guess between two


def _link_php(imap: ImpactMap, path: str, f: FileFacts, by_suffix, composer: Dict[str, str]) -> None:
    short_index: Dict[str, List[str]] = {}
    for fqn, where in imap.classes.items():
        short_index.setdefault(fqn.rsplit("\\", 1)[-1].lower(), []).append(where)
    for literal in f.includes:
        target = _resolve_include(path, literal, by_suffix, imap.files)
        if target:
            imap.link(path, target, "include")
        else:
            imap.unresolved += 1
    for literal in f.templates:
        hits = by_suffix.get(literal)
        if hits:
            imap.link(path, hits[0], "template")
    refs = set(f.class_refs) | {fqn for _, fqn in f.uses}
    for name in refs:
        target = _resolve_class(name, f, imap, short_index)
        if target:
            imap.link(path, target, "class")
        else:
            package = _composer_package(name, f, composer)
            if package:
                imap.packages.setdefault(package, set()).add(path)
    for call in f.calls:
        target = imap.functions.get(call)
        if target:
            imap.link(path, target, "function")


def _composer_packages(inv: Inventory) -> Dict[str, str]:
    """composer.json requirements, keyed by the namespace head they usually use (guzzlehttp -> guzzlehttp/guzzle)."""
    try:
        data = json.loads(inv.read("composer.json") or "{}")
    except ValueError:
        return {}
    found = {}
    for name in list((data.get("require") or {})) + list((data.get("require-dev") or {})):
        if "/" in name:
            vendor, package = name.lower().split("/", 1)
            found.setdefault(vendor.replace("-", ""), name)
            found.setdefault(package.replace("-", ""), name)
    return found


def _composer_package(name: str, f: FileFacts, composer: Dict[str, str]) -> Optional[str]:
    aliases = {alias.lower(): fqn for alias, fqn in f.uses}
    fqn = aliases.get(name.split("\\")[0].lower(), name)
    head = fqn.split("\\")[0].lower()
    return composer.get(head)


def _js_aliases(inv: Inventory) -> List[Tuple[str, str]]:
    """Path aliases from tsconfig/jsconfig (e.g. "@/*" -> "src/*"); "@/" -> "src/" is the default."""
    aliases: List[Tuple[str, str]] = []
    for name in ("tsconfig.json", "jsconfig.json"):
        text = inv.read(name)
        if not text:
            continue
        try:
            options = json.loads(re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)).get("compilerOptions") or {}
        except ValueError:
            continue
        base = (options.get("baseUrl") or ".").strip("./")
        for key, targets in (options.get("paths") or {}).items():
            if targets:
                target = posixpath.normpath(posixpath.join(base, targets[0].rstrip("*")))
                aliases.append((key.rstrip("*"), target.rstrip("/") + "/"))
    if not any(prefix == "@/" for prefix, _ in aliases):
        aliases.append(("@/", "src/"))
    return aliases


def _resolve_js(base: str, files: Dict[str, str]) -> Optional[str]:
    base = posixpath.normpath(base)
    candidates = [base] + [base + ext for ext in JS_EXTENSIONS] + [f"{base}/index{ext}" for ext in JS_EXTENSIONS]
    if base.endswith((".js", ".jsx", ".mjs")):  # TypeScript projects import "./x.js" for x.ts
        candidates += [base.rsplit(".", 1)[0] + ext for ext in (".ts", ".tsx")]
    return next((c for c in candidates if c in files), None)


def _link_js(imap: ImpactMap, path: str, f: FileFacts, aliases: List[Tuple[str, str]]) -> None:
    for spec in f.imports:
        target = None
        if spec.startswith("."):
            target = _resolve_js(posixpath.join(posixpath.dirname(path), spec), imap.files)
        else:
            for prefix, folder in aliases:
                if spec.startswith(prefix):
                    target = _resolve_js(folder + spec[len(prefix):], imap.files)
                    break
            if target is None and not spec.startswith(("http:", "https:", "node:")):
                package = "/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0]
                if package in NODE_BUILTINS:
                    continue
                if not any(spec.startswith(prefix) for prefix, _ in aliases):
                    imap.packages.setdefault(package, set()).add(path)
                    continue
        if target:
            imap.link(path, target, "import")
        elif spec.startswith(".") or any(spec.startswith(p) for p, _ in aliases):
            imap.unresolved += 1


def _link_python(imap: ImpactMap, path: str, f: FileFacts) -> None:
    package_dir = posixpath.dirname(path)
    for spec in f.imports:
        if spec.startswith("."):
            dots = len(spec) - len(spec.lstrip("."))
            base = package_dir
            for _ in range(dots - 1):
                base = posixpath.dirname(base)
            module = spec.lstrip(".")
            rel = posixpath.join(base, module.replace(".", "/")) if module else base
            target = _python_file(rel, imap.files)
        else:
            rel = spec.replace(".", "/")
            target = _python_file(rel, imap.files) or _python_file(posixpath.join(package_dir, rel), imap.files)
            if target is None:
                top = spec.split(".")[0]
                if top not in PYTHON_STDLIB and not _python_file(top, imap.files) and \
                        not any(p.startswith(top + "/") for p in imap.files):
                    imap.packages.setdefault(top, set()).add(path)
        if target:
            imap.link(path, target, "import")


def _python_file(rel: str, files: Dict[str, str]) -> Optional[str]:
    rel = posixpath.normpath(rel) if rel else ""
    for candidate in (rel + ".py", posixpath.join(rel, "__init__.py")):
        if candidate in files:
            return candidate
    return None


# ---- questions ----------------------------------------------------------------------------------------

def resolve_target(imap: ImpactMap, target: str) -> Tuple[str, List[str], List[str]]:
    """(kind, label, files the target lives in or is used by directly). kind: file | class |
    function | hook | package | unknown."""
    target = target.strip().strip("/")
    if target in imap.files:
        return "file", [target], [target]
    suffix = [p for p in imap.files if p.endswith("/" + target)]
    if len(suffix) == 1:
        return "file", suffix, suffix
    name = target.lstrip("\\")
    for fqn, where in imap.classes.items():
        if fqn.lower() == name.lower() or fqn.rsplit("\\", 1)[-1].lower() == name.lower():
            return "class", [fqn], [where]
    if name.rstrip("()") in imap.functions:
        return "function", [name.rstrip("()")], [imap.functions[name.rstrip("()")]]
    if name in imap.hooks:
        return "hook", [name], sorted(imap.hooks[name].get("added", set()))
    package = next((p for p in imap.packages if p.lower() == name.lower()), None)
    if package:
        return "package", [package], []
    return "unknown", suffix, []


def impact(imap: ImpactMap, target: str, max_depth: int = 6) -> Dict[str, Any]:
    kind, label, origin = resolve_target(imap, target)
    if kind == "unknown":
        return {"target": target, "kind": "unknown", "found": False, "candidates": label[:10],
                "message": "Not found in the map. Give a file path, a class, a function, a WordPress hook or a package."}
    if kind == "package":
        direct = sorted(imap.packages[label[0]])
        start = set(direct)
    else:
        direct = sorted({u for o in origin for u in imap.used_by.get(o, set())} - set(origin))
        start = set(origin)
    depth: Dict[str, int] = {p: 0 for p in start}
    queue = deque(start)
    while queue:
        current = queue.popleft()
        if depth[current] >= max_depth:
            continue
        for user in imap.used_by.get(current, ()):
            if user not in depth:
                depth[user] = depth[current] + 1
                queue.append(user)
    affected = sorted((p for p in depth if p not in origin), key=lambda p: (depth[p], p))
    everything = set(affected) | set(origin)
    entries = sorted(p for p in everything & imap.entry_points() if not imap.is_test(p))
    tests = sorted(p for p in everything if imap.is_test(p))
    reach = len([p for p in affected if not imap.is_test(p)])
    level = "wide" if reach >= WIDE_IMPACT_FILES or len(entries) >= 5 else "moderate" if reach >= 3 else "contained"
    return {
        "target": target, "kind": kind, "found": True, "name": label[0], "defined_in": origin,
        "used_directly_by": [{"path": p, "how": _how(imap, p, origin) if kind != "package" else ["package"]}
                             for p in direct][:200],
        "affected": [{"path": p, "steps": depth[p]} for p in affected][:500],
        "affected_count": len(affected), "entry_points": entries[:100], "tests": tests[:100],
        "level": level, "untested": not tests,
        "advice": _advice(level, entries, tests),
    }


def _how(imap: ImpactMap, user: str, origin: List[str]) -> List[str]:
    return sorted(set().union(*(imap.kinds.get((user, o), set()) for o in origin)))


def _advice(level: str, entries: List[str], tests: List[str]) -> str:
    if level == "wide":
        text = "Wide impact: change in small steps and re-test every page listed."
    elif level == "moderate":
        text = "Moderate impact: check the pages listed after the change."
    else:
        text = "Contained: few other files depend on this."
    if not tests:
        text += " No automated test covers this; add one before changing it, or test by hand."
    return text


def summary(imap: ImpactMap, limit: int = 10) -> Dict[str, Any]:
    """For the Health Check / Audit report: how connected the code is and where changes ripple most."""
    def reach(path: str) -> int:
        seen, queue = {path}, deque([path])
        while queue:
            for user in imap.used_by.get(queue.popleft(), ()):
                if user not in seen:
                    seen.add(user)
                    queue.append(user)
        return len(seen) - 1
    candidates = [p for p in imap.files if imap.used_by.get(p) and not imap.is_test(p)]
    hotspots = sorted(({"path": p, "used_directly_by": len(imap.used_by[p]), "affects": reach(p)} for p in candidates),
                      key=lambda h: (-h["affects"], -h["used_directly_by"], h["path"]))[:limit]
    mapped = sum(1 for p in imap.files if imap.uses.get(p) or imap.used_by.get(p))
    return {"files": len(imap.files), "linked_files": mapped, "links": imap.link_count,
            "packages": len(imap.packages), "entry_points": len(imap.entry_points()),
            "hooks": len(imap.hooks), "unresolved": imap.unresolved, "truncated": imap.truncated, "hotspots": hotspots}


def package_reach(imap: ImpactMap, packages: Iterable[str]) -> List[Dict[str, Any]]:
    """For each outside package (e.g. one with a known vulnerability): the files using it directly."""
    out = []
    lowered = {p.lower(): p for p in imap.packages}
    for name in packages:
        key = lowered.get(name.lower())
        if key:
            users = sorted(imap.packages[key])
            out.append({"package": name, "files": users[:20], "count": len(users)})
    return out
