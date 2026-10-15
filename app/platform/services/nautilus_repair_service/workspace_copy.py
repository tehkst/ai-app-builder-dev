"""Scratch copies of a sandbox and change detection for Nautilus repair proposals.

Nautilus edits a disposable copy, never the approved sandbox itself; the difference between
the copy and the original becomes the reviewable proposal.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".agent_outputs"}
MAX_COPY_BYTES = 50 * 1024 * 1024
MAX_DIFF_LINES = 400


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _tracked_files(root: Path) -> Dict[str, Path]:
    files: Dict[str, Path] = {}
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)
        for name in names:
            path = Path(current, name)
            if path.is_symlink() or not path.is_file():
                continue
            files[path.relative_to(root).as_posix()] = path
    return files


def make_scratch_copy(sandbox_root: Path) -> Path:
    total = sum(path.stat().st_size for path in _tracked_files(sandbox_root).values())
    if total > MAX_COPY_BYTES:
        raise ValueError(f"Sandbox is too large to copy for a repair proposal ({total} bytes).")
    scratch = Path(tempfile.mkdtemp(prefix="nautilus-repair-"))
    target = scratch / "workspace"
    shutil.copytree(sandbox_root, target, symlinks=True,
                    ignore=shutil.ignore_patterns(*IGNORED_DIRS))
    return target


def remove_scratch_copy(copy_root: Path) -> None:
    shutil.rmtree(copy_root.parent, ignore_errors=True)


def snapshot_files(root: Path) -> Dict[str, bytes]:
    """Raw content of every tracked file, taken right after copying: the proposal's baseline.
    Comparing against this (not the live sandbox) keeps concurrent sandbox edits from being
    mistaken for the starting state."""
    return {relative: path.read_bytes() for relative, path in _tracked_files(root).items()}


def _decode(data: Optional[bytes]) -> Optional[str]:
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def diverged_paths(baseline: Dict[str, bytes], live_root: Path, paths: List[str]) -> List[str]:
    """Paths whose live sandbox content no longer matches the baseline snapshot."""
    live = _tracked_files(live_root)
    diverged = []
    for relative in paths:
        current = live[relative].read_bytes() if relative in live else None
        if current != baseline.get(relative):
            diverged.append(relative)
    return diverged


def detect_changes(baseline: Dict[str, bytes], copy_root: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Text files the agent created or modified in the copy relative to the baseline snapshot,
    plus changes the executor can't apply (deletions and binary files), reported separately
    rather than dropped silently."""
    after = _tracked_files(copy_root)
    changed: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []
    for relative in sorted(set(baseline) - set(after)):
        unsupported.append({"path": relative, "change": "deleted", "reason": "The repair executor cannot delete files."})
    for relative, new_path in sorted(after.items()):
        new_bytes = new_path.read_bytes()
        old_bytes = baseline.get(relative)
        if new_bytes == old_bytes:
            continue
        new_text, old_text = _decode(new_bytes), _decode(old_bytes)
        if new_text is None or (old_bytes is not None and old_text is None):
            unsupported.append({"path": relative, "change": "binary", "reason": "Only text files can be repaired."})
            continue
        diff = list(difflib.unified_diff((old_text or "").splitlines(), new_text.splitlines(),
                                         f"a/{relative}", f"b/{relative}", lineterm=""))
        truncated = len(diff) > MAX_DIFF_LINES
        changed.append({
            "path": relative,
            "change": "modified" if old_bytes is not None else "created",
            "before_sha256": sha256_text(old_text) if old_bytes is not None else None,
            "after_sha256": sha256_text(new_text),
            "replacement_content": new_text,
            "diff": "\n".join(diff[:MAX_DIFF_LINES]) + ("\n... (diff truncated)" if truncated else ""),
        })
    return {"changed": changed, "unsupported": unsupported}
