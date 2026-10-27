"""Tool-calling chat adapters for the providers in runtime/provider_router.py.

The existing ``invoke_provider`` path is prompt-in/text-out; these adapters add native
function calling on the same endpoints and credentials (with a longer timeout and retries, below):
OpenAI Responses API (``function_call`` / ``function_call_output`` items) and DeepSeek
chat completions (OpenAI-compatible ``tools`` / ``tool_calls``).
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.platform.nautilus.messages import ChatFn, ChatTurn, Message, ToolCall, parse_arguments
from app.platform.runtime.ai_provider import (
    OPENAI_API_URL, AIProviderError, AIProviderTimeoutError, _extract_output_text, _openai_api_key,
    _openai_timeout_seconds,
)
from app.platform.runtime.deepseek_provider import DEEPSEEK_API_URL, _deepseek_api_key, _timeout_seconds
from app.platform.runtime.provider_router import SUPPORTED_MODELS, default_model, selected_provider

OPENAI_ITEMS_KEY = "_openai_items"  # raw Responses output items, replayed verbatim to OpenAI

# An employee's turn carries the whole conversation so far (on a real codebase: 50k+ tokens), so it
# can take minutes; one slow or busy-provider answer must not fail an Audit or a mission that has
# already spent money. Tool chats get a longer limit, and timeouts and temporary errors are retried.
DEFAULT_AGENT_TIMEOUT_SECONDS = 300
RETRY_DELAYS = (5.0, 20.0)  # seconds before the 2nd and 3rd attempt
RETRYABLE_HTTP = {408, 409, 429, 500, 502, 503, 504}
_sleep = time.sleep  # replaced in checks


def agent_timeout(provider_timeout: int) -> int:
    """At least ASF_AGENT_TIMEOUT_SECONDS (default 300, 30-900) for tool-calling turns."""
    try:
        wanted = int(os.getenv("ASF_AGENT_TIMEOUT_SECONDS", str(DEFAULT_AGENT_TIMEOUT_SECONDS)))
    except ValueError:
        wanted = DEFAULT_AGENT_TIMEOUT_SECONDS
    return max(provider_timeout, min(max(wanted, 30), 900))


def _retryable(error: AIProviderError) -> bool:
    if isinstance(error, AIProviderTimeoutError):
        return True
    status = getattr(error, "http_status", None)
    return status in RETRYABLE_HTTP or (status is None and getattr(error, "network", False))


def _post_with_retries(url: str, api_key: str, payload: Dict[str, Any], timeout: int, label: str) -> Dict[str, Any]:
    for attempt, delay in enumerate((*RETRY_DELAYS, None)):
        try:
            return _post_json(url, api_key, payload, timeout, label)
        except AIProviderError as exc:
            if delay is None or not _retryable(exc):
                if attempt:
                    raise type(exc)(f"{exc} (after {attempt + 1} attempts)") from exc
                raise
            _sleep(delay)
    raise AssertionError("unreachable")


def _post_json(url: str, api_key: str, payload: Dict[str, Any], timeout: int, label: str) -> Dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (socket.timeout, TimeoutError) as exc:
        raise AIProviderTimeoutError(f"{label} request timed out after {timeout} seconds") from exc
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        error = AIProviderError(f"{label} request failed with {exc.code}: {body}")
        error.http_status = exc.code
        raise error from exc
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), socket.timeout):
            raise AIProviderTimeoutError(f"{label} request timed out after {timeout} seconds") from exc
        error = AIProviderError(f"{label} request failed: {exc}")
        error.network = True  # connection reset, DNS hiccup: worth another try
        raise error from exc


def _public(message: Message) -> Message:
    return {key: value for key, value in message.items() if not key.startswith("_") and value is not None}


# ---- OpenAI Responses API -------------------------------------------------------------

def to_openai_input(messages: List[Message]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "tool":
            items.append({"type": "function_call_output", "call_id": message["tool_call_id"],
                          "output": str(message.get("content") or "")})
        elif role == "assistant" and message.get(OPENAI_ITEMS_KEY):
            items.extend(message[OPENAI_ITEMS_KEY])
        elif role == "assistant":
            if message.get("content"):
                items.append({"role": "assistant", "content": str(message["content"])})
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                items.append({"type": "function_call", "call_id": call["id"], "name": function.get("name"),
                              "arguments": function.get("arguments") or "{}"})
        else:
            items.append({"role": role, "content": str(message.get("content") or "")})
    return items


def parse_openai_response(raw: Dict[str, Any], model: str) -> ChatTurn:
    output = [item for item in raw.get("output") or [] if isinstance(item, dict)]
    calls = [
        ToolCall(str(item.get("call_id")), str(item.get("name")), parse_arguments(item.get("arguments")),
                 str(item.get("arguments") or ""))
        for item in output if item.get("type") == "function_call"
    ]
    text = _extract_output_text({"output": [i for i in output if i.get("type") == "message"]})
    assistant: Message = {"role": "assistant", "content": text, OPENAI_ITEMS_KEY: output}
    if calls:
        assistant["tool_calls"] = [{"id": c.call_id, "type": "function",
                                    "function": {"name": c.name, "arguments": c.raw_arguments}} for c in calls]
    return ChatTurn(text, calls, assistant, "openai", model, raw.get("usage") or {})


def openai_chat(model: str) -> ChatFn:
    def chat(messages: List[Message], tools: List[Dict[str, Any]]) -> ChatTurn:
        api_key = _openai_api_key()
        if not api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured")
        payload: Dict[str, Any] = {"model": model, "input": to_openai_input(messages)}
        if tools:
            payload["tools"] = [{"type": "function", "strict": False, **tool} for tool in tools]
        raw = _post_with_retries(OPENAI_API_URL, api_key, payload, agent_timeout(_openai_timeout_seconds()), "OpenAI")
        return parse_openai_response(raw, model)

    return chat


# ---- DeepSeek chat completions --------------------------------------------------------

def parse_deepseek_response(raw: Dict[str, Any], model: str) -> ChatTurn:
    choices = raw.get("choices") or []
    message = (choices[0].get("message") if choices and isinstance(choices[0], dict) else None) or {}
    assistant = _public({**message, "role": "assistant"})
    calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        calls.append(ToolCall(str(call.get("id")), str(function.get("name")),
                              parse_arguments(function.get("arguments")), str(function.get("arguments") or "")))
    return ChatTurn(str(message.get("content") or "").strip(), calls, assistant, "deepseek", model,
                    raw.get("usage") or {})


def deepseek_chat(model: str) -> ChatFn:
    def chat(messages: List[Message], tools: List[Dict[str, Any]]) -> ChatTurn:
        api_key = _deepseek_api_key()
        if not api_key:
            raise AIProviderError("DEEPSEEK_API_KEY is not configured")
        payload: Dict[str, Any] = {"model": model, "messages": [_public(m) for m in messages], "stream": False}
        if tools:
            payload["tools"] = [{"type": "function", "function": tool} for tool in tools]
        raw = _post_with_retries(DEEPSEEK_API_URL, api_key, payload, agent_timeout(_timeout_seconds()), "DeepSeek")
        return parse_deepseek_response(raw, model)

    return chat


def build_chat_fn(provider: Optional[str] = None, model: Optional[str] = None) -> ChatFn:
    """Tool-calling chat function for the configured (or given) provider and model."""
    explicit = str(provider or "").strip().lower()
    if explicit and explicit not in SUPPORTED_MODELS:
        raise AIProviderError("The selected AI provider is not supported.")
    active = selected_provider(provider)
    selected_model = model or default_model(active)
    if selected_model not in SUPPORTED_MODELS[active]:
        raise AIProviderError("The selected model is not supported by the configured AI provider.")
    return deepseek_chat(selected_model) if active == "deepseek" else openai_chat(selected_model)
