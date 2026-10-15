"""Context compaction for long agent runs (modelled on goose's context_mgmt).

When the conversation reaches ``threshold`` of the model's context limit, the middle of
the history is replaced by a summary. The system prompt, the original goal and the most
recent messages are kept verbatim; the kept tail never starts with an orphaned tool
result, so tool-call/result pairs stay intact.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from app.platform.agent_loop.messages import Message, estimate_tokens, first_index_not_tool, user_message

DEFAULT_CONTEXT_LIMIT_TOKENS = 128_000
DEFAULT_COMPACTION_THRESHOLD = 0.8
DEFAULT_KEEP_RECENT = 6
SUMMARY_INPUT_CHARS_PER_MESSAGE = 4_000

Summarizer = Callable[[str], str]

SUMMARY_INSTRUCTIONS = (
    "Summarise the following earlier part of an AI agent's working session so the agent can "
    "continue without it. Keep: decisions made, files created or changed (with paths), "
    "commands run and whether they passed, errors still unresolved, and remaining steps. "
    "Be factual and concise; do not invent details."
)


def needs_compaction(messages: List[Message], context_limit: int = DEFAULT_CONTEXT_LIMIT_TOKENS,
                     threshold: float = DEFAULT_COMPACTION_THRESHOLD) -> bool:
    return estimate_tokens(messages) >= int(context_limit * threshold)


def _head_length(messages: List[Message]) -> int:
    """System prompt (if any) plus the first user message (the goal)."""
    length = 0
    if messages and messages[0].get("role") == "system":
        length = 1
    if len(messages) > length and messages[length].get("role") == "user":
        length += 1
    return length


def render_for_summary(messages: List[Message]) -> str:
    lines: List[str] = []
    for message in messages:
        role = message.get("role")
        content = str(message.get("content") or "")[:SUMMARY_INPUT_CHARS_PER_MESSAGE]
        if role == "tool":
            lines.append(f"[tool result {message.get('tool_call_id')}]\n{content}")
            continue
        lines.append(f"[{role}]\n{content}" if content else f"[{role}]")
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            lines.append(f"  -> called {function.get('name')}({str(function.get('arguments'))[:500]})")
    return "\n".join(lines)


def compact_messages(messages: List[Message], summarizer: Optional[Summarizer],
                     keep_recent: int = DEFAULT_KEEP_RECENT) -> List[Message]:
    head = _head_length(messages)
    tail_start = first_index_not_tool(messages, max(head, len(messages) - keep_recent))
    if tail_start is None or tail_start <= head:
        return list(messages)
    middle = messages[head:tail_start]
    if not middle:
        return list(messages)

    summary: Optional[str] = None
    if summarizer is not None:
        try:
            summary = summarizer(SUMMARY_INSTRUCTIONS + "\n\n" + render_for_summary(middle)).strip()
        except Exception:
            summary = None
    if summary:
        note = f"[Context compacted: {len(middle)} earlier messages were summarised.]\n{summary}"
    else:
        note = (
            f"[Context compacted: {len(middle)} earlier messages were removed and could not be "
            "summarised. Re-check workspace state with list_files/read_file before relying on "
            "earlier results.]"
        )
    return list(messages[:head]) + [user_message(note)] + list(messages[tail_start:])
