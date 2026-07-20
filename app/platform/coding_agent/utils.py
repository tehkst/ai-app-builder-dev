"""
Coding Agent utility functions.

Public utilities that can be used across the platform.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


def clear_pycache(path: str) -> None:
    """Delete __pycache__ directories under the given path.

    Use this to force recompilation after modifying Python source files.
    Safe to call on any path — only __pycache__ dirs are removed.

    Args:
        path: Root directory path to scan for __pycache__ directories.
    """
    root = Path(path).resolve()
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(str(root)):
        if dirpath.endswith("__pycache__"):
            shutil.rmtree(dirpath, ignore_errors=True)
