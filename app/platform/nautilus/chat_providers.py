"""Tool-calling chat adapters for the providers in runtime/provider_router.py.

The existing ``invoke_provider`` path is prompt-in/text-out; these adapters add native
function calling on the same endpoints and credentials (with a longer timeout and retries, below):
OpenAI Responses API (``function_call`` / ``function_call_output`` items) and DeepSeek
chat completions (OpenAI-compatible ``tools`` / ``tool_calls``).
"""
from __future__ import annotations

import http.client
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
# The per-read socket timeout only catches silence. Found in the pilot: an Audit waited 2+ hours on
# one request (DeepSeek keeps a slow request alive by sending blank lines, and a Mac that sleeps
# leaves a half-dead connection). So each request also has a wall-clock deadline (time.time counts
# time asleep; time.monotonic doesn't on macOS), checked between reads.
SILENCE_SECONDS = 60
_sleep = time.sleep  # replaced in checks
_now = time.time  # replaced in checks


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
    deadline = _now() + timeout
    try:
        with urllib.request.urlopen(request, timeout=min(timeout, SILENCE_SECONDS)) as response:
            body = _read_until(response, deadline, timeout, label).decode("utf-8", errors="replace")
    except (socket.timeout, TimeoutError) as exc:
        raise AIProviderTimeoutError(f"{label} sent nothing for {SILENCE_SECONDS} seconds") from exc
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        error = AIProviderError(f"{label} request failed with {exc.code}: {body}")
        error.http_status = exc.code
        raise error from exc
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), socket.timeout):
            raise AIProviderTimeoutError(f"{label} sent nothing for {SILENCE_SECONDS} seconds") from exc
        error = AIProviderError(f"{label} request failed: {exc}")
        error.network = True  # connection reset, DNS hiccup: worth another try
        raise error from exc
    except (http.client.HTTPException, ConnectionError) as exc:
        # Found in the pilot: DeepSeek sometimes drops the connection part-way through a long
        # answer (IncompleteRead, RemoteDisconnected); urllib doesn't wrap errors while reading.
        error = AIProviderError(f"{label} connection dropped mid-answer: {exc!r}")
        error.network = True
        raise error from exc
    return _assemble_stream(body, label) if payload.get("stream") else _json_object(body, label)


def _assemble_stream(body: str, label: str) -> Dict[str, Any]:
    """Rebuild a chat-completions answer from its streamed pieces. Found in the pilot: without
    streaming, DeepSeek at peak hours goes silent for over a minute while it thinks, and the
    connection drops or the silence check fires; streamed, something arrives every few seconds."""
    if not any(line.startswith("data:") for line in body.splitlines()):
        return _json_object(body, label)  # an error answered as plain JSON
    content: List[str] = []
    reasoning: List[str] = []
    calls: Dict[int, Dict[str, Any]] = {}
    usage: Dict[str, Any] = {}
    finish, done = None, False
    for line in body.splitlines():
        if not line.startswith("data:"):
            continue  # blank lines and ": keep-alive" comments
        data = line[5:].strip()
        if data == "[DONE]":
            done = True
            continue
        try:
            chunk = json.loads(data)
        except ValueError:
            chunk = None
        if not isinstance(chunk, dict):
            error = AIProviderError(f"{label} returned an unreadable piece of its answer: {data[:200]}")
            error.network = True
            raise error
        if chunk.get("error"):
            raise AIProviderError(f"{label} reported an error mid-answer: {json.dumps(chunk['error'])[:300]}")
        usage = chunk.get("usage") or usage
        for choice in chunk.get("choices") or []:
            delta = (choice.get("delta") if isinstance(choice, dict) else None) or {}
            finish = choice.get("finish_reason") or finish
            content.append(delta.get("content") or "")
            reasoning.append(delta.get("reasoning_content") or "")
            for piece in delta.get("tool_calls") or []:
                if not isinstance(piece, dict):
                    continue
                call = calls.setdefault(int(piece.get("index") or 0),
                                        {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                call["id"] = piece.get("id") or call["id"]
                function = piece.get("function") or {}
                call["function"]["name"] += function.get("name") or ""
                call["function"]["arguments"] += function.get("arguments") or ""
    if not done and finish is None:
        error = AIProviderError(f"{label} connection dropped mid-answer (the stream ended early)")
        error.network = True
        raise error
    message: Dict[str, Any] = {"role": "assistant", "content": "".join(content)}
    if "".join(reasoning):
        message["reasoning_content"] = "".join(reasoning)
    if calls:
        message["tool_calls"] = [calls[index] for index in sorted(calls)]
    return {"choices": [{"message": message, "finish_reason": finish}], "usage": usage}


def _json_object(body: str, label: str) -> Dict[str, Any]:
    """Found in the pilot: a turn that took four minutes came back as something other than a JSON
    object and paused a mission with "'NoneType' object has no attribute 'get'". A cut-off or
    empty answer is the provider's hiccup, so it is reported as such and retried."""
    try:
        raw = json.loads(body)
    except ValueError:
        raw = None
    if isinstance(raw, dict):
        return raw
    snippet = " ".join(body.split())[:200] or "an empty body"
    error = AIProviderError(f"{label} returned an unreadable response: {snippet}")
    error.network = True
    raise error


def _read_until(response: Any, deadline: float, timeout: int, label: str) -> bytes:
    """The whole body, unless the deadline passes first (keep-alive blank lines keep arriving)."""
    chunks: List[bytes] = []
    while True:
        if _now() > deadline:
            raise AIProviderTimeoutError(f"{label} request timed out after {timeout} seconds")
        chunk = response.read1(65536) if hasattr(response, "read1") else response.read(65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


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
    message = message if isinstance(message, dict) else {}
    if not all(isinstance(call, dict) for call in message.get("tool_calls") or []):
        message = {**message, "tool_calls": [c for c in message["tool_calls"] if isinstance(c, dict)] or None}
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
        payload: Dict[str, Any] = {"model": model, "messages": [_public(m) for m in messages], "stream": True,
                                   "stream_options": {"include_usage": True}}
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
