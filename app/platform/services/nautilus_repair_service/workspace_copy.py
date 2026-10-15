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


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def detect_changes(original_root: Path, copy_root: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Text files the agent created or modified in the copy, plus changes the executor can't
    apply (deletions and binary files), reported separately rather than dropped silently."""
    before, after = _tracked_files(original_root), _tracked_files(copy_root)
    changed: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []
    for relative in sorted(set(before) - set(after)):
        unsupported.append({"path": relative, "change": "deleted", "reason": "The repair executor cannot delete files."})
    for relative, new_path in sorted(after.items()):
        new_text = _read_text(new_path)
        old_path = before.get(relative)
        old_text = _read_text(old_path) if old_path else None
        if new_text is None or (old_path is not None and old_text is None):
            if old_path is None or new_path.read_bytes() != old_path.read_bytes():
                unsupported.append({"path": relative, "change": "binary", "reason": "Only text files can be repaired."})
            continue
        if old_path is not None and new_text == old_text:
            continue
        diff = list(difflib.unified_diff((old_text or "").splitlines(), new_text.splitlines(),
                                         f"a/{relative}", f"b/{relative}", lineterm=""))
        truncated = len(diff) > MAX_DIFF_LINES
        changed.append({
            "path": relative,
            "change": "modified" if old_path else "created",
            "before_sha256": sha256_text(old_text) if old_path else None,
            "after_sha256": sha256_text(new_text),
            "replacement_content": new_text,
            "diff": "\n".join(diff[:MAX_DIFF_LINES]) + ("\n... (diff truncated)" if truncated else ""),
        })
    return {"changed": changed, "unsupported": unsupported}
