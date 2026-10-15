"""Runaway-loop protection and oversized tool output handling (from goose's
tool_monitor and large_response_handler)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from app.platform.agent_loop.messages import ToolCall

DEFAULT_MAX_REPETITIONS = 3
DEFAULT_LARGE_OUTPUT_CHARS = 40_000
PREVIEW_CHARS = 2_000
OUTPUT_DIR_NAME = ".agent_outputs"


class ToolRepetitionMonitor:
    """Blocks a tool call once the identical call (same name and arguments) has been
    made ``max_repetitions`` times in a row."""

    def __init__(self, max_repetitions: int = DEFAULT_MAX_REPETITIONS) -> None:
        self.max_repetitions = max(1, max_repetitions)
        self._last_signature: Optional[str] = None
        self._count = 0

    def allow(self, call: ToolCall) -> bool:
        signature = call.signature()
        if signature == self._last_signature:
            self._count += 1
        else:
            self._last_signature = signature
            self._count = 1
        return self._count <= self.max_repetitions

    def reset(self) -> None:
        self._last_signature = None
        self._count = 0


class LargeOutputHandler:
    """Writes tool output above a size threshold to a file inside the workspace and
    returns a short preview plus the path, so big logs don't flood the context window."""

    def __init__(self, workspace_root: Optional[str], threshold_chars: int = DEFAULT_LARGE_OUTPUT_CHARS) -> None:
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.threshold_chars = threshold_chars

    def process(self, call: ToolCall, output: str) -> str:
        if len(output) <= self.threshold_chars:
            return output
        if self.workspace_root is None:
            return output[: self.threshold_chars] + (
                f"\n\n[Output truncated: {len(output)} characters total; no workspace available to store the full text.]"
            )
        out_dir = self.workspace_root / OUTPUT_DIR_NAME
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{call.name}-{int(time.time() * 1000)}-{call.call_id[-8:] or 'call'}.txt"
        safe_name = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in filename)
        target = out_dir / safe_name
        target.write_text(output, encoding="utf-8")
        relative = target.relative_to(self.workspace_root).as_posix()
        return (
            f"[Output was {len(output)} characters, too large to include. Full text saved to "
            f"'{relative}'. Use read_file or run_command (e.g. grep, tail) on it if you need more.]\n\n"
            f"First {PREVIEW_CHARS} characters:\n{output[:PREVIEW_CHARS]}"
        )
