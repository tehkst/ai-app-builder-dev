"""Provider-neutral conversation types for the tool-calling agent loop.

Messages are kept in the chat-completions shape (role/content/tool_calls/tool_call_id)
because both providers' tool-calling contracts map onto it cleanly. Provider adapters
convert to and from their own wire formats.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

Message = Dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: Dict[str, Any]
    raw_arguments: str = ""

    def signature(self) -> str:
        """Stable identity used for repetition detection (name + canonical args)."""
        return self.name + ":" + json.dumps(self.arguments, sort_keys=True, default=str)


@dataclass(frozen=True)
class ChatTurn:
    """One model response: optional text plus zero or more requested tool calls."""

    text: str
    tool_calls: List[ToolCall]
    assistant_message: Message
    provider: str = ""
    model: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)


# (messages, tool_schemas) -> ChatTurn. Tool schemas use the neutral shape from
# ToolRegistry.schemas(); adapters translate them per provider.
ChatFn = Callable[[List[Message], List[Dict[str, Any]]], ChatTurn]


def system_message(content: str) -> Message:
    return {"role": "system", "content": content}


def user_message(content: str) -> Message:
    return {"role": "user", "content": content}


def tool_result_message(call_id: str, content: str) -> Message:
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def parse_arguments(raw: Any) -> Dict[str, Any]:
    """Decode a tool call's arguments; malformed JSON becomes an explicit error marker
    rather than a silently empty dict, so the tool can report it back to the model."""
    if isinstance(raw, dict):
        return raw
    if raw in (None, ""):
        return {}
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        return {"__invalid_json__": str(raw)}
    return decoded if isinstance(decoded, dict) else {"__invalid_json__": str(raw)}


def message_text_length(message: Message) -> int:
    length = len(str(message.get("content") or ""))
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        length += len(str(function.get("name") or "")) + len(str(function.get("arguments") or ""))
    return length


def estimate_tokens(messages: List[Message]) -> int:
    """Rough token estimate (~4 chars per token). Neither provider exposes a local
    tokenizer through this codebase, so this is an approximation, not a count."""
    return sum(message_text_length(message) for message in messages) // 4 + 4 * len(messages)


def first_index_not_tool(messages: List[Message], start: int) -> Optional[int]:
    """Earliest index >= start that does not begin with an orphaned tool result."""
    for index in range(start, len(messages)):
        if messages[index].get("role") != "tool":
            return index
    return None
