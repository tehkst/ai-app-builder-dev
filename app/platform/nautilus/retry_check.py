"""Check for provider retries (found in the real-code pilot: one DeepSeek turn on a 230-file
codebase took over 90 seconds and failed an Audit that had already cost $1.42). Tool-calling turns
get at least ASF_AGENT_TIMEOUT_SECONDS; timeouts, rate limits, provider 5xx and network errors are
retried twice; a bad key or a bad request fails at once. No network: _post_json is replaced."""
from __future__ import annotations

import os
from typing import List

from app.platform.nautilus import chat_providers as cp
from app.platform.runtime.ai_provider import AIProviderError, AIProviderTimeoutError


def _http(status: int) -> AIProviderError:
    error = AIProviderError(f"DeepSeek request failed with {status}: x")
    error.http_status = status
    return error


def _network() -> AIProviderError:
    error = AIProviderError("DeepSeek request failed: <urlopen error [Errno 54] Connection reset by peer>")
    error.network = True
    return error


def run(script: List[object]) -> tuple:
    """Feed _post_json the scripted outcomes; return (result or error, calls, sleeps, timeouts seen)."""
    calls, sleeps, timeouts = [], [], []
    original, original_sleep = cp._post_json, cp._sleep

    def fake(url, key, payload, timeout, label):
        timeouts.append(timeout)
        outcome = script[len(calls)]
        calls.append(outcome)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    cp._post_json, cp._sleep = fake, sleeps.append
    try:
        try:
            result = cp._post_with_retries("u", "k", {}, 300, "DeepSeek")
        except AIProviderError as exc:
            result = exc
    finally:
        cp._post_json, cp._sleep = original, original_sleep
    return result, len(calls), sleeps, timeouts


def main() -> None:
    ok = {"choices": []}
    timeout = AIProviderTimeoutError("DeepSeek request timed out after 300 seconds")
    assert run([ok])[:3] == (ok, 1, [])
    assert run([timeout, ok])[:3] == (ok, 2, [5.0]), "a slow turn is retried"
    assert run([_http(429), _http(503), ok])[:3] == (ok, 3, [5.0, 20.0]), "busy provider: retried twice"
    assert run([_network(), ok])[:2] == (ok, 2), "connection reset: retried"
    result, calls, sleeps, _ = run([timeout, timeout, timeout])
    assert isinstance(result, AIProviderTimeoutError) and calls == 3 and "after 3 attempts" in str(result), result
    for status in (400, 401, 402, 403, 404):
        result, calls, _, _ = run([_http(status), ok])
        assert isinstance(result, AIProviderError) and calls == 1, (status, calls)
        assert "attempts" not in str(result), "a single failure is reported as it was"

    os.environ.pop("ASF_AGENT_TIMEOUT_SECONDS", None)
    assert cp.agent_timeout(90) == 300 and cp.agent_timeout(400) == 400, "never shorter than the provider's own"
    os.environ["ASF_AGENT_TIMEOUT_SECONDS"] = "5"
    assert cp.agent_timeout(10) == 30
    os.environ["ASF_AGENT_TIMEOUT_SECONDS"] = "99999"
    assert cp.agent_timeout(90) == 900
    os.environ["ASF_AGENT_TIMEOUT_SECONDS"] = "abc"
    assert cp.agent_timeout(90) == 300
    os.environ.pop("ASF_AGENT_TIMEOUT_SECONDS")

    # The DeepSeek and OpenAI tool chats go through the retrying path with the agent timeout.
    seen = []
    original = cp._post_with_retries
    cp._post_with_retries = lambda url, key, payload, timeout, label: seen.append((label, timeout)) or {
        "choices": [{"message": {"content": "done"}}], "output": []}
    os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    try:
        cp.deepseek_chat("deepseek-v4-flash")([{"role": "user", "content": "hi"}], [])
        cp.openai_chat("gpt-5.5")([{"role": "user", "content": "hi"}], [])
    finally:
        cp._post_with_retries = original
    assert [label for label, _ in seen] == ["DeepSeek", "OpenAI"] and all(t >= 300 for _, t in seen), seen
    print("PROVIDER RETRY CHECK PASSED")


if __name__ == "__main__":
    main()
