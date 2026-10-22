"""Graph-based context for Orca's employees (step 5d).

Instead of leaving each employee to browse the whole workspace, every briefing gets a short map of
the code that matters for its task, built from the impact map (app/platform/impact_map):

- the task's files, the files they use, and the files that use them (so a change's ripple is known);
- an outline of each (classes, functions, imports), never the full contents, so the employee reads
  only what it needs with read_file.

Outlines are cached by the SHA-256 of the file's content, so unchanged files are never re-read or
re-parsed; the impact map is rebuilt only when a source file's size or modification time changes.
Nothing here calls an AI provider.
"""
from __future__ import annotations

import hashlib
import os
import re
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from app.platform.impact_map import build_map, summary
from app.platform.impact_map.graph import ImpactMap

MAX_CONTEXT_CHARS = 6_000
MAX_NEIGHBOURS = 12
MAX_OUTLINE_ITEMS = 12

MAX_OUTLINES = 20_000  # cached outlines (LRU); each is one short line
MAX_MAPS = 16  # workspaces whose maps are kept (LRU): finished client jobs drop out
_OUTLINES: "OrderedDict[str, str]" = OrderedDict()  # content sha256 -> outline
# workspace -> (fingerprint, current map, first map seen: keeps the dependants of files deleted since)
_MAPS: "OrderedDict[str, Tuple[str, ImpactMap, ImpactMap]]" = OrderedDict()
_LOCK = threading.Lock()
STATS = {"outline_hits": 0, "outline_misses": 0, "map_builds": 0}

_DEFS = [
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?|class)\s+([A-Za-z_$][\w$]*)", re.M),
    re.compile(r"^\s*export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)", re.M),
    re.compile(r"^\s*(?:abstract\s+|final\s+)*(?:class|interface|trait|enum)\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+)*function\s+&?([A-Za-z_]\w*)", re.M),
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)|^\s*class\s+([A-Za-z_]\w*)", re.M),
]


def outline(text: str) -> str:
    """Names a file defines, in order (deduplicated), as one short line."""
    found = sorted((m.start(), next((g for g in m.groups() if g), "")) for pattern in _DEFS for m in pattern.finditer(text))
    names: List[str] = []
    for _, name in found:  # in file order
        if name and name not in names:
            names.append(name)
    shown = names[:MAX_OUTLINE_ITEMS]
    more = f" (+{len(names) - len(shown)} more)" if len(names) > len(shown) else ""
    return (", ".join(shown) + more) if shown else "(no named definitions)"


def file_outline(root: Path, rel: str) -> Optional[str]:
    """The outline of one workspace file, cached by content hash (unchanged file: no re-parse)."""
    try:
        data = (root / rel).read_bytes()
    except OSError:
        return None
    digest = hashlib.sha256(data).hexdigest()
    with _LOCK:
        if digest in _OUTLINES:
            STATS["outline_hits"] += 1
            _OUTLINES.move_to_end(digest)
            return _OUTLINES[digest]
    result = outline(data.decode("utf-8", errors="replace"))
    with _LOCK:
        STATS["outline_misses"] += 1
        _OUTLINES[digest] = result
        while len(_OUTLINES) > MAX_OUTLINES:
            _OUTLINES.popitem(last=False)
    return result


def _fingerprint(root: Path, imap: Optional[ImpactMap]) -> str:
    """Cheap change detector: size and modification time of every mapped source file."""
    parts: List[str] = []
    for rel in sorted(imap.files) if imap else []:
        try:
            st = (root / rel).stat()
            parts.append(f"{rel}:{st.st_size}:{st.st_mtime_ns}")
        except OSError:
            parts.append(f"{rel}:gone")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def workspace_map(workspace: str) -> ImpactMap:
    """The impact map of a workspace, rebuilt only when a mapped file changed (or files appeared)."""
    return _maps(workspace)[0]


def _maps(workspace: str) -> Tuple[ImpactMap, ImpactMap]:
    """(current map, first map seen for this workspace)."""
    root = Path(workspace)
    with _LOCK:
        cached = _MAPS.get(workspace)
        if cached:
            _MAPS.move_to_end(workspace)
    if cached and cached[0] == _fingerprint(root, cached[1]) and not _new_sources(root, cached[1]):
        return cached[1], cached[2]
    imap = build_map(workspace)
    with _LOCK:
        STATS["map_builds"] += 1
        _MAPS[workspace] = (_fingerprint(root, imap), imap, cached[2] if cached else imap)
        _MAPS.move_to_end(workspace)
        while len(_MAPS) > MAX_MAPS:
            _MAPS.popitem(last=False)
        return imap, _MAPS[workspace][2]


def _new_sources(root: Path, imap: ImpactMap) -> bool:
    """A source file the map would now include (e.g. a builder added a module), judged with the
    same inventory rules build_map uses: skipped folders, generated and oversized files, symlinks
    and, in a git checkout, untracked files never count, so they never force a rebuild."""
    if imap.truncated:
        return False  # past the file limit the map can't grow anyway
    from app.platform.codebase_health.inventory import build_inventory

    return any(item.path not in imap.files for item in build_inventory(root).files)


def _block(root: Path, title: str, paths: Iterable[str], budget: List[int]) -> str:
    lines = []
    for rel in paths:
        text = file_outline(root, rel)
        if text is None:
            continue
        line = f"- `{rel}`: {text}"
        if budget[0] - len(line) < 0:
            lines.append("- ... (more files: use list_files / read_file)")
            break
        budget[0] -= len(line)
        lines.append(line)
    return f"{title}\n" + "\n".join(lines) + "\n" if lines else ""


def task_context(workspace: str, files: List[str]) -> str:
    """The code connected to a task's files, with outlines. Empty when nothing is mapped."""
    if not files:
        return ""
    try:
        imap, first = _maps(workspace)
    except Exception:  # context is a help, never a blocker
        return ""
    root = Path(workspace)
    wanted = list(dict.fromkeys(_clean(f) for f in files))
    own = [f for f in wanted if f in imap.files]
    # Files deleted since the workspace was first mapped: their former dependants are what may break.
    deleted = [f for f in wanted if f not in imap.files and f in first.files and not (root / f).exists()]
    uses = sorted({u for f in own for u in imap.uses.get(f, set())} - set(own))[:MAX_NEIGHBOURS]
    used_by = sorted(({u for f in own for u in imap.used_by.get(f, set())} |
                      {u for f in deleted for u in first.used_by.get(f, set()) if (root / u).exists()})
                     - set(own))[:MAX_NEIGHBOURS]
    budget = [MAX_CONTEXT_CHARS]
    gone = ("Deleted by this change:\n" + "\n".join(f"- `{f}` (deleted)" for f in deleted) + "\n") if deleted else ""
    parts = [_block(root, "Files of this task (outline):", own, budget), gone,
             _block(root, "They use (read these to understand what they rely on):", uses, budget),
             _block(root, "Used by (a change here can break these; keep them working):", used_by, budget)]
    body = "".join(p for p in parts if p)
    if not body:
        return ""
    return ("## Code connected to this task\nFrom the code map (outlines only; read_file for detail). You don't "
            "need to browse the rest of the project.\n" + body)


def plan_context(workspace: str) -> str:
    """For the architect: the entry points and the most connected files of the workspace."""
    try:
        imap = workspace_map(workspace)
    except Exception:
        return ""
    if not imap.files:
        return ""
    info = summary(imap, limit=8)
    root = Path(workspace)
    budget = [MAX_CONTEXT_CHARS // 2]
    entries = sorted(imap.entry_points())[:10]
    parts = [_block(root, "Entry points:", entries, budget),
             _block(root, "Most connected files (changes here ripple furthest):", [h["path"] for h in info["hotspots"]], budget)]
    body = "".join(p for p in parts if p)
    return (f"## Code map\n{info['files']} source files, {info['links']} links between them.\n" + body) if body else ""


def _clean(path: str) -> str:
    return os.path.normpath(str(path).replace("\\", "/")).replace(os.sep, "/").lstrip("/")
