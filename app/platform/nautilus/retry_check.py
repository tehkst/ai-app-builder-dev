"""Check for provider retries (found in the real-code pilot: one DeepSeek turn on a 230-file
codebase took over 90 seconds and failed an Audit that had already cost $1.42). Tool-calling turns
get at least ASF_AGENT_TIMEOUT_SECONDS; timeouts, rate limits, provider 5xx and network errors are
retried twice; a bad key or a bad request fails at once; a request that keeps the connection alive
with blank lines (or outlives a Mac's sleep) ends at its wall-clock deadline. No network."""
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


class _Response:
    """A provider response that sends `chunks`, advancing the fake clock `step` seconds per read."""

    def __init__(self, chunks: List[bytes], clock: List[float], step: float) -> None:
        self.chunks, self.clock, self.step = list(chunks), clock, step

    def read1(self, size: int) -> bytes:
        self.clock[0] += self.step
        return self.chunks.pop(0) if self.chunks else b""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Dropping(_Response):
    def __init__(self, error: Exception) -> None:
        super().__init__([], [0.0], 0.0)
        self.error = error

    def read1(self, size: int) -> bytes:
        raise self.error


def check_deadline() -> None:
    import urllib.request

    clock = [1000.0]
    original_open, original_now = urllib.request.urlopen, cp._now
    cp._now = lambda: clock[0]
    try:
        # A normal answer in several pieces (leading keep-alive blank lines are fine JSON whitespace).
        urllib.request.urlopen = lambda req, timeout: _Response([b"\n", b"\n", b'{"choi', b'ces": []}'], clock, 1.0)
        assert cp._post_json("https://x", "k", {}, 300, "DeepSeek") == {"choices": []}
        # Blank lines forever: ends at the deadline instead of hanging (the pilot's 2-hour Audit).
        urllib.request.urlopen = lambda req, timeout: _Response([b"\n"] * 10_000, clock, 10.0)
        try:
            cp._post_json("https://x", "k", {}, 300, "DeepSeek")
            raise AssertionError("must time out")
        except AIProviderTimeoutError as exc:
            assert "300 seconds" in str(exc)
        # The Mac slept for an hour mid-request: wall-clock time counts, so the next read ends it.
        urllib.request.urlopen = lambda req, timeout: _Response([b"\n", b"\n"], clock, 3600.0)
        try:
            cp._post_json("https://x", "k", {}, 300, "DeepSeek")
            raise AssertionError("must time out after sleep")
        except AIProviderTimeoutError:
            pass
        # Found in the pilot: an answer that isn't a JSON object is a retryable provider hiccup, not a crash.
        for body in (b"null", b"", b'{"choi', b"[]"):
            urllib.request.urlopen = lambda req, timeout, body=body: _Response([body], clock, 0.0)
            try:
                cp._post_json("https://x", "k", {}, 300, "DeepSeek")
                raise AssertionError(f"must refuse {body!r}")
            except AIProviderError as exc:
                assert "unreadable response" in str(exc) and cp._retryable(exc), (body, exc)
        # Found in the pilot: the connection dropped part-way through the answer.
        import http.client

        for dropped in (http.client.IncompleteRead(b""), http.client.RemoteDisconnected("closed"), ConnectionResetError()):
            urllib.request.urlopen = lambda req, timeout, dropped=dropped: _Dropping(dropped)
            try:
                cp._post_json("https://x", "k", {}, 300, "DeepSeek")
                raise AssertionError(f"must refuse {dropped!r}")
            except AIProviderError as exc:
                assert "dropped" in str(exc) and cp._retryable(exc), exc
        seen = []
        urllib.request.urlopen = lambda req, timeout: seen.append(timeout) or _Response([b"{}"], clock, 0.0)
        cp._post_json("https://x", "k", {}, 300, "DeepSeek")
        assert seen == [cp.SILENCE_SECONDS], "silence is detected sooner than the whole deadline"
    finally:
        urllib.request.urlopen, cp._now = original_open, original_now


def main() -> None:
    check_deadline()
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
    turn = cp.parse_deepseek_response({"choices": [{"message": {"content": "x", "tool_calls": [None, {
        "id": "c1", "function": {"name": "list_files", "arguments": "{}"}}]}}]}, "deepseek-v4-pro")
    assert [c.name for c in turn.tool_calls] == ["list_files"] and None not in turn.assistant_message["tool_calls"]
    assert cp.parse_deepseek_response({"choices": [{"message": "odd"}]}, "m").text == ""
    check_unexpected_errors_are_named()
    print("PROVIDER RETRY CHECK PASSED")


def check_unexpected_errors_are_named() -> None:
    """A bug in our own code during a turn still pauses the mission, but the reason says it's a bug."""
    import logging
    from app.platform.nautilus.loop import _describe

    logging.getLogger("ai_factory.agent_loop").disabled = True
    try:
        assert _describe(AIProviderError("DeepSeek request failed with 503: busy")) == "DeepSeek request failed with 503: busy"
        described = _describe(AttributeError("'NoneType' object has no attribute 'get'"))
        assert described.startswith("unexpected AttributeError (a bug") and "NoneType" in described, described
    finally:
        logging.getLogger("ai_factory.agent_loop").disabled = False


if __name__ == "__main__":
    main()
