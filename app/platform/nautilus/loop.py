"""Tool-calling agent loop (modelled on goose's agents/agent.rs reply loop).

The model is called repeatedly: each response may request tool calls, whose results are
fed back, until the model answers without calling a tool or ``max_turns`` is reached.
Every call passes through the permission policy, the repetition monitor and the large
output handler; the conversation is compacted when it nears the context limit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Callable, Dict, List, Optional

from app.platform.nautilus.compaction import (
    DEFAULT_COMPACTION_THRESHOLD, DEFAULT_CONTEXT_LIMIT_TOKENS, Summarizer, compact_messages, needs_compaction,
)
from app.platform.nautilus.guards import LargeOutputHandler, ToolRepetitionMonitor
from app.platform.nautilus.messages import ChatFn, Message, ToolCall, system_message, tool_result_message, user_message
from app.platform.nautilus.permissions import PermissionPolicy
from app.platform.nautilus.tools import ToolRegistry, missing_required
from app.platform.nautilus.usage import add_usage
from app.platform.runtime.ai_provider import AIProviderError

logger = logging.getLogger("ai_factory.agent_loop")  # ai_factory.* reaches the service log

DEFAULT_MAX_TURNS = 25
MAX_BLOCKED_REPEATS = 3  # stop the run after this many blocked repeat attempts


@dataclass
class ToolCallRecord:
    turn: int
    name: str
    arguments: Dict[str, Any]
    outcome: str  # "ok" | "error" | "denied" | "repeated" | "unknown_tool"
    detail: str = ""


@dataclass
class AgentRunResult:
    status: str  # "completed" | "max_turns" | "stopped_repetition" | "provider_error"
    final_text: str
    turns: int
    messages: List[Message]
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    compactions: int = 0
    error: Optional[str] = None
    usage: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # "provider/model" -> token totals


@dataclass
class AgentLoopConfig:
    max_turns: int = DEFAULT_MAX_TURNS
    context_limit_tokens: int = DEFAULT_CONTEXT_LIMIT_TOKENS
    compaction_threshold: float = DEFAULT_COMPACTION_THRESHOLD
    max_repetitions: int = 3


class AgentLoop:
    def __init__(self, *, chat: ChatFn, tools: ToolRegistry, system_prompt: str,
                 permissions: Optional[PermissionPolicy] = None, workspace_root: Optional[str] = None,
                 summarizer: Optional[Summarizer] = None, config: Optional[AgentLoopConfig] = None,
                 on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> None:
        self.chat = chat
        self.tools = tools
        self.system_prompt = system_prompt
        self.permissions = permissions or PermissionPolicy(mode="approve")
        if self.permissions.workspace_root is None:
            self.permissions.workspace_root = workspace_root  # confines smart-mode auto-approval
        self.summarizer = summarizer
        self.config = config or AgentLoopConfig()
        self.large_output = LargeOutputHandler(workspace_root)
        self.on_event = on_event

    def run(self, goal: str, history: Optional[List[Message]] = None) -> AgentRunResult:
        messages = list(history) if history else [system_message(self.system_prompt)]
        messages.append(user_message(goal))
        return self.resume(messages)

    def resume(self, messages: List[Message]) -> AgentRunResult:
        try:
            return self._resume(messages)
        finally:
            self.large_output.cleanup()  # saved outputs are scratch for this run only

    def _resume(self, messages: List[Message]) -> AgentRunResult:
        records: List[ToolCallRecord] = []
        monitor = ToolRepetitionMonitor(self.config.max_repetitions)
        compactions = blocked_repeats = 0
        last_text = ""
        usage: Dict[str, Dict[str, Any]] = {}
        for turn in range(1, self.config.max_turns + 1):
            if needs_compaction(messages, self.config.context_limit_tokens, self.config.compaction_threshold):
                messages = compact_messages(messages, self.summarizer)
                compactions += 1
                self._emit("compacted", {"turn": turn, "messages": len(messages)})
            try:
                reply = self.chat(messages, self.tools.schemas())
            except Exception as exc:
                return AgentRunResult("provider_error", last_text, turn, messages, records, compactions,
                                      _describe(exc), usage)
            if reply.provider or reply.usage:
                add_usage(usage.setdefault(f"{reply.provider}/{reply.model}", {}), reply.provider, reply.model, reply.usage)
            messages.append(reply.assistant_message)
            last_text = reply.text or last_text
            self._emit("model_turn", {"turn": turn, "tool_calls": [c.name for c in reply.tool_calls]})
            if not reply.tool_calls:
                return AgentRunResult("completed", reply.text, turn, messages, records, compactions, usage=usage)
            for call in reply.tool_calls:
                content, record = self._execute(call, turn, monitor)
                records.append(record)
                blocked_repeats += record.outcome == "repeated"
                messages.append(tool_result_message(call.call_id, content))
            if blocked_repeats >= MAX_BLOCKED_REPEATS:
                return AgentRunResult("stopped_repetition", last_text, turn, messages, records, compactions,
                                      "The agent kept repeating the same tool call.", usage)
        return AgentRunResult("max_turns", last_text, self.config.max_turns, messages, records, compactions, usage=usage)

    def _execute(self, call: ToolCall, turn: int, monitor: ToolRepetitionMonitor):
        def record(outcome: str, detail: str = "") -> ToolCallRecord:
            target = call.arguments.get("path") or call.arguments.get("command") or ""
            self._emit("tool_call", {"turn": turn, "name": call.name, "outcome": outcome,
                                     "target": str(target)[:160]})  # path or command; listeners decide what to keep
            return ToolCallRecord(turn, call.name, call.arguments, outcome, detail)

        tool = self.tools.get(call.name)
        if tool is None:
            return (f"Error: unknown tool '{call.name}'. Available tools: {', '.join(self.tools.names())}.",
                    record("unknown_tool"))
        if not monitor.allow(call):
            return ("Error: you have already made this exact call several times in a row. It will not be "
                    "run again. Try a different approach, or finish and explain what is blocking you.",
                    record("repeated"))
        if "__invalid_json__" in call.arguments:
            return "Error: the tool arguments were not valid JSON. Retry with a valid JSON object.", record("error")
        missing = missing_required(tool, call.arguments)
        if missing:
            return f"Error: missing required argument(s): {', '.join(missing)}.", record("error")
        decision = self.permissions.decide(tool, call)
        if not decision.allowed:
            return (f"Permission denied for {call.name}: {decision.reason}. Do not retry this action; "
                    "describe what should happen instead.", record("denied", decision.reason))
        try:
            output = tool.handler(call.arguments)
        except Exception as exc:
            return f"Error running {call.name}: {exc}", record("error", str(exc))
        return self.large_output.process(call, str(output)), record("ok")

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        if self.on_event is not None:
            try:
                self.on_event(event, payload)
            except Exception:
                pass


def _describe(exc: Exception) -> str:
    """A provider's own error reads as it is; anything else is a bug on our side, so the pause
    reason names the exception type and the traceback goes to the log."""
    if isinstance(exc, AIProviderError):
        return str(exc)
    logger.error("unexpected error during a model turn", exc_info=exc)
    return f"unexpected {type(exc).__name__} (a bug, see the service log): {exc}"
