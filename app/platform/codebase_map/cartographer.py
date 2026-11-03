"""The AI half of the Codebase Map: the Codebase Cartographer decides what the parts of the app are
and names and describes every file and endpoint in plain words. Everything mechanical (scanning,
assigning files, connecting them, Health) is done by scan.py and build.py at no AI cost.

1. Architecture: the Cartographer reads the scan summary and a redacted copy of the code (read-only;
   commands go to the container sandbox) and returns the parts, outside services, extra connections,
   flows and a tour. build.check_architecture names any problems and the Cartographer gets one
   round to fix them; whatever is still broken is dropped.
2. Descriptions: one short run per batch of files (grouped by part), from a worksheet digest of
   each file, so most files never need opening.
3. Updates: an earlier map's architecture is reused (redrawn only when asked, or when too much new
   code fits nowhere) and descriptions carry over to files whose content or signature is unchanged,
   including moved and renamed files. Only new and changed files are described again.
"""
from __future__ import annotations

import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.platform.clients.redaction import redact, redact_all, redacted_copy
from app.platform.codebase_map import build
from app.platform.codebase_map.scan import Scan, build_scan, summary, worksheet
from app.platform.nautilus.messages import ChatFn

ARCHITECTURE_TURNS = 40
FIX_TURNS = 12
DESCRIBE_TURNS = 6
BATCH_FILES = 60
MAX_DESCRIBED = 1500
PARALLEL = 3

_STR = {"type": "string"}
_ARR = {"type": "array", "items": _STR}
ARCHITECTURE_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["project", "nodes"],
    "properties": {
        "project": {"type": "object", "required": ["name", "summary"], "properties": {"name": _STR, "summary": _STR}},
        "nodes": {"type": "array", "items": {"type": "object", "required": ["id", "label", "kind", "summary"], "properties": {
            "id": _STR, "label": _STR, "kind": {"type": "string", "enum": list(build.KINDS)}, "parent": _STR,
            "summary": _STR, "details": _STR, "paths": _ARR, "exclude": _ARR, "packages": _ARR, "hosts": _ARR}}},
        "edges": {"type": "array", "items": {"type": "object", "required": ["from", "to"], "properties": {
            "from": _STR, "to": _STR, "kind": {"type": "string", "enum": list(build.EDGE_KINDS)}, "label": _STR,
            "description": _STR}}},
        "flows": {"type": "array", "items": {"type": "object", "required": ["title", "steps"], "properties": {
            "id": _STR, "title": _STR, "description": _STR,
            "steps": {"type": "array", "items": {"type": "object", "required": ["node"], "properties": {
                "node": _STR, "note": _STR}}}}}},
        "tour": {"type": "array", "items": {"type": "object", "required": ["node", "title", "note"], "properties": {
            "node": _STR, "title": _STR, "note": _STR}}},
    },
}
DESCRIBE_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["files"],
    "properties": {
        "files": {"type": "array", "items": {"type": "object", "required": ["path", "name", "description"],
                                             "properties": {"path": _STR, "name": _STR, "description": _STR}}},
        "routes": {"type": "array", "items": {"type": "object", "required": ["key", "name", "description"],
                                              "properties": {"key": _STR, "name": _STR, "description": _STR}}},
    },
}

PLAIN = ("Write for the app's owner, who may not read code: say what each thing does for the business in "
         "everyday words (\"Takes card payments at checkout\", not \"Stripe API wrapper\"). Labels are short "
         "(\"Main server\", \"Online shop\"). The real paths are shown next to every name, so don't repeat them.")
TECHNICAL = "Write for developers: precise and technical, naming frameworks and patterns where useful."

# Replaceable for checks (a scripted Cartographer); production builds the pinned provider's chat.
chat_factory: Callable[[str, str], ChatFn] = lambda provider, model: _provider_chat(provider, model)


def _provider_chat(provider: str, model: str) -> ChatFn:
    from app.platform.nautilus.chat_providers import build_chat_fn

    return build_chat_fn(provider, model)


class MapError(RuntimeError):
    usage: List[Dict[str, Any]] = []


def _cartographer():
    from app.platform.orca.workforce import load_workforce

    return load_workforce().for_responsibility("map_codebase")


def _run(assignment: str, workspace: str, ai: Tuple[str, str], schema: Dict[str, Any], turns: int,
         usage: List[Dict[str, Any]], resume_from=None):
    from app.platform.orca.employee_runner import run_employee

    return run_employee(_cartographer(), assignment=assignment, workspace_root=workspace, chat=chat_factory(*ai),
                        output_schema=schema, allow_writes=False, allow_execution=False, max_turns=turns,
                        sandboxed=True, usage_sink=usage, resume_from=resume_from)


# ---- 1. architecture -------------------------------------------------------------------------------

def architecture_assignment(project: str, scan: Scan, audience: str, draft: Optional[Dict[str, Any]] = None) -> str:
    draft_text = ""
    if draft:
        import json

        draft_text = ("\n## The current map\nThe code changed since this architecture was written; update it rather "
                      "than starting over (keep ids that still fit):\n" + json.dumps(draft)[:12000] + "\n")
    return (f"## Codebase\n{project}\n\n## Scan summary\n{redact(summary(scan))}\n{draft_text}\n"
            "## Deliverable\nRead just enough to understand the shape of the app: the README, manifests "
            "(package.json, composer.json, pyproject, requirements), the entry points and one or two files per "
            "candidate part (several read_file calls per turn). Then call final_output with the architecture:\n"
            "- project: name and a 1-3 sentence summary of what the app does and for whom;\n"
            "- nodes: 3-9 top-level parts (no parent); give a part children only when it holds more than about 15 "
            "files (then 3-12 children), so a small app has a few parts, never one per file. Each has an id "
            "(letters, digits, '_', '-', '.'; children dotted by parent like api.orders), a short label, a kind ("
            + ", ".join(build.KINDS) + "), a one-sentence summary, and paths: globs that claim its files "
            "(** any folders, * within one folder, {a,b} alternatives; a plain folder path claims everything "
            "inside it). The deepest matching node gets each file, so a parent can claim web/** and children "
            "narrower folders. exclude globs carve files back out and apply to all children. Together the globs "
            "must cover over 90% of the files in the scan;\n"
            "- external nodes (kind external, no paths) for the databases and outside services the code really "
            "uses, with packages (package names as in the scan, wildcards allowed) and/or hosts (like "
            "api.stripe.com);\n"
            "- edges: only connections the scan can't see (queues, scheduled jobs, webhooks coming in, calls "
            "through URLs kept in settings, the database a part reads and writes). from/to are node ids or file "
            "paths; kind is one of " + ", ".join(build.EDGE_KINDS) + ";\n"
            "- flows: 1-3 walkthroughs of the app's main jobs, each 2-8 steps of {node, note}, node being a node "
            "id or file path, notes narrated for a newcomer;\n"
            "- tour: 3-8 stops {node, title, note} in the order a newcomer should see them: what the app is, "
            "the apps people use, the main server, outside services, ending on an important screen.\n\n"
            f"## Style\n{TECHNICAL if audience == 'developers' else PLAIN} Never repeat a secret's value.\n\n"
            f"## Budget\nYou have {ARCHITECTURE_TURNS} turns. Call final_output by turn {ARCHITECTURE_TURNS - 5} "
            "at the latest; the shape of the system matters, not a code review.")


def _fix_message(problems: List[str]) -> Dict[str, str]:
    return {"role": "user", "content": "The map builder checked your architecture and found these problems:\n- "
            + "\n- ".join(problems) + "\n\nFix them and call final_output again with the complete corrected "
            "architecture (every node, not only the changed ones)."}


def run_architecture(workspace: str, project: str, scan: Scan, ai: Tuple[str, str], audience: str,
                     usage: List[Dict[str, Any]], draft: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
    result = _run(architecture_assignment(project, scan, audience, draft), workspace, ai, ARCHITECTURE_SCHEMA,
                  ARCHITECTURE_TURNS, usage)
    if result.run.status == "provider_error":
        raise MapError(f"The AI provider failed ({result.run.error or 'no detail'}); make the map again.")
    if not result.output:
        raise MapError(f"The Codebase Cartographer finished without an architecture ({result.run.status}); make the map again.")
    arch = build.clean_architecture(result.output)
    problems = build.check_architecture(scan, arch)
    if problems:
        fixed = _run("", workspace, ai, ARCHITECTURE_SCHEMA, FIX_TURNS, usage,
                     resume_from=list(result.run.messages) + [_fix_message(problems)])
        if fixed.output:
            candidate = build.clean_architecture(fixed.output)
            remaining = build.check_architecture(scan, candidate)
            if len(remaining) <= len(problems):
                arch, problems = candidate, remaining
    return redact_all(build.drop_invalid(scan, arch)), problems


# ---- 2. descriptions -------------------------------------------------------------------------------

def describe_assignment(project: str, parts: List[Tuple[Dict[str, Any], str]], audience: str) -> str:
    """One briefing for a batch: the worksheet of each part in it (small parts share a batch)."""
    sheets = "\n\n".join(f"## Part: {part.get('label')} ({part.get('kind')})\n{part.get('summary', '')}\n\n{redact(sheet)}"
                         for part, sheet in parts)
    return (f"## Codebase\n{project}\n\n# Worksheet\n{sheets}\n\n## Deliverable\nCall final_output with a name and a "
            "description for EVERY file and endpoint in the worksheet, using the worksheet's exact paths and endpoint "
            "keys. A name is 2-5 words (\"Checkout page\", \"Sends order emails\"); a description is one or two sentences "
            "on what it does and why it matters. The worksheet is usually enough; read a file only when it truly isn't.\n\n"
            f"## Style\n{TECHNICAL if audience == 'developers' else PLAIN} Never repeat a secret's value.")


def _batches(scan: Scan, owner: Dict[str, str], paths: List[str]) -> List[List[Tuple[str, List[str], List[str]]]]:
    """Batches of up to BATCH_FILES files, each a list of (part, its files, their endpoints). Parts stay
    together where they fit, and small parts share a batch: every batch costs a full briefing."""
    by_node: Dict[str, List[str]] = {}
    for p in paths:
        by_node.setdefault(owner.get(p, build.UNASSIGNED), []).append(p)
    serves: Dict[str, List[str]] = {}
    for r in scan.routes:
        serves.setdefault(r.file, []).append(r.key)
    chunks = []
    for node_id, files in sorted(by_node.items()):
        for i in range(0, len(files), BATCH_FILES):
            chunk = files[i:i + BATCH_FILES]
            chunks.append((node_id, chunk, sorted({k for p in chunk for k in serves.get(p, [])})))
    batches: List[List[Tuple[str, List[str], List[str]]]] = []
    for chunk in chunks:
        if batches and sum(len(c[1]) for c in batches[-1]) + len(chunk[1]) <= BATCH_FILES:
            batches[-1].append(chunk)
        else:
            batches.append([chunk])
    return batches


def run_descriptions(workspace: str, project: str, scan: Scan, arch: Dict[str, Any], paths: List[str],
                     route_keys: Optional[set], ai: Tuple[str, str], audience: str,
                     usage: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, str]]]:
    """Names and descriptions for these files (and their endpoints, limited to `route_keys` when given)."""
    owner = build.assign(scan, arch)
    parts = {n["id"]: n for n in arch["nodes"]}
    parts[build.UNASSIGNED] = {"label": "Unassigned", "kind": "feature", "summary": ""}
    jobs = [[(node_id, files, [k for k in keys if route_keys is None or k in route_keys]) for node_id, files, keys in batch]
            for batch in _batches(scan, owner, paths)]
    out: Dict[str, Dict[str, Dict[str, str]]] = {"files": {}, "routes": {}}
    if not jobs:
        return out
    sinks: List[List[Dict[str, Any]]] = [[] for _ in jobs]

    def one(index: int) -> Optional[Dict[str, Any]]:
        brief = describe_assignment(project, [(parts[node_id], worksheet(scan, files, keys))
                                             for node_id, files, keys in jobs[index]], audience)
        result = _run(brief, workspace, ai, DESCRIBE_SCHEMA, DESCRIBE_TURNS, sinks[index])
        if result.run.status == "provider_error":
            raise MapError(f"The AI provider failed ({result.run.error or 'no detail'}); make the map again.")
        return result.output

    try:
        with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
            results = list(pool.map(one, range(len(jobs))))
    finally:
        for sink in sinks:
            usage.extend(sink)
    for batch, output in zip(jobs, results):
        wanted_files = {p for _, files, _ in batch for p in files}
        wanted_keys = {k for _, _, keys in batch for k in keys}
        for item in (output or {}).get("files") or []:
            if item.get("path") in wanted_files:
                out["files"][item["path"]] = {"name": str(item.get("name", ""))[:60],
                                              "description": str(item.get("description", ""))[:400]}
        for item in (output or {}).get("routes") or []:
            if item.get("key") in wanted_keys:
                out["routes"][item["key"]] = {"name": str(item.get("name", ""))[:60],
                                              "description": str(item.get("description", ""))[:400]}
    return redact_all(out)


# ---- 3. updates ---------------------------------------------------------------------------------

def carry_over(scan: Scan, previous: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], List[str]]:
    """Descriptions an earlier map already has for unchanged files (same content or same signature,
    or the same content under a new path), and the files that still need describing."""
    kept: Dict[str, Dict[str, Dict[str, str]]] = {"files": {}, "routes": {}}
    if not previous:
        return kept, list(scan.files)
    old_files = {f["path"]: f for f in previous.get("files") or []}
    by_sha = {f["sha"]: f for f in old_files.values() if f.get("sha") and f.get("description")}
    old_routes = {r["key"]: r for r in previous.get("routes") or []}
    todo = []
    for path, info in scan.files.items():
        old = old_files.get(path)
        if old and old.get("description") and (old.get("sha") == info.sha or old.get("signature") == info.signature):
            source = old
        else:
            source = by_sha.get(info.sha)
        if source:
            kept["files"][path] = {"name": source["name"], "description": source["description"]}
        else:
            todo.append(path)
    for r in scan.routes:
        old = old_routes.get(r.key)
        if old and old.get("description") and r.file in kept["files"]:
            kept["routes"][r.key] = {"name": old["name"], "description": old["description"]}
    return kept, todo


def _priority(paths: List[str]) -> List[str]:
    """Most useful first when a huge codebase is over the description budget: tests and config last."""
    return sorted(paths, key=lambda p: (bool(build.TEST_PATH.search(p)), bool(build.CONFIG_PATH.search(p)), p))


# ---- the whole map ----------------------------------------------------------------------------------

def make_map(local_path: str, project: str, ai: Tuple[str, str], audience: str = "everyone",
             previous: Optional[Dict[str, Any]] = None, redraw: bool = False) -> Dict[str, Any]:
    """Scan, ask the Cartographer, build. `previous` is the last map's saved result for this code."""
    from app.platform.clients.audit import project_dir_name

    scan = build_scan(local_path)
    if not scan.files:
        raise MapError("There's no source code to map in this folder.")
    usage: List[Dict[str, Any]] = []
    scratch = Path(tempfile.mkdtemp(prefix="asf-map-"))
    try:
        copy = scratch / project_dir_name(project)
        redacted_copy(local_path, str(copy))  # what the AI provider may see
        try:
            old_arch = (previous or {}).get("architecture")
            arch, problems = (old_arch, []) if old_arch and not redraw else (None, [])
            if arch is not None:
                arch = build.drop_invalid(scan, build.clean_architecture(_as_raw(arch)))
                if any("belong to no node" in p for p in build.check_architecture(scan, arch)):
                    arch = None  # too much new code fits nowhere: update the architecture
            if arch is None:
                arch, problems = run_architecture(str(copy), project, scan, ai, audience, usage,
                                                  draft=_as_raw(old_arch) if old_arch and not redraw else None)
            kept, todo = carry_over(scan, None if redraw else (previous or {}).get("graph"))
            todo = _priority(todo)[:MAX_DESCRIBED]
            todo_routes = {r.key for r in scan.routes if r.key not in kept["routes"]}
            fresh = run_descriptions(str(copy), project, scan, arch, todo, todo_routes, ai, audience, usage)
        except MapError as exc:
            exc.usage = usage  # paid replies are recorded even when the map fails
            raise
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    descriptions = {"files": {**kept["files"], **fresh["files"]}, "routes": {**kept["routes"], **fresh["routes"]}}
    graph = build.build_graph(scan, arch, descriptions)
    return {"graph": graph, "architecture": arch, "problems": problems, "ai_usage": usage,
            "carried": len(kept["files"]), "described": len(fresh["files"])}


def _as_raw(arch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """A saved (cleaned) architecture in the Cartographer's own format, to clean or show again."""
    if not arch:
        return None
    return {**arch, "flows": [{**f, "steps": [{"node": s["ref"], "note": s.get("note", "")} for s in f["steps"]]}
                              for f in arch.get("flows") or []],
            "tour": [{"node": s["ref"], "title": s.get("title", ""), "note": s.get("note", "")} for s in arch.get("tour") or []]}
