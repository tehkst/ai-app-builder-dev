from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any

from app.platform.runtime.ai_provider import AIProviderError, AIProviderResult, AIProviderTimeoutError


DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_SECRET_NAME = "DEEPSEEK_API_KEY"
DEFAULT_DEEPSEEK_TIMEOUT_SECONDS = 90


def _deepseek_api_key() -> str | None:
    from app.platform.credential_vault.service import resolve_credential

    return resolve_credential(DEEPSEEK_SECRET_NAME)


def deepseek_configured() -> bool:
    return bool(_deepseek_api_key())


def invoke_deepseek(
    *, prompt: str, system: str | None = None, model: str | None = None, images: list[str] | None = None
) -> AIProviderResult:
    # DeepSeek's public hosted API (api.deepseek.com) is text-only for both v4-pro and
    # v4-flash - there is no image/vision input format in its chat completions contract,
    # so an attached image's pixels genuinely cannot reach the model this way. Say so
    # honestly in the prompt rather than silently dropping it or pretending it was seen.
    if images:
        prompt = (
            prompt
            + "\n\n(Note: image attachment(s) were supplied, but the DeepSeek API has no "
            "image input capability, so their visual content is not visible to you here. "
            "Tell the founder plainly that you cannot see the image and ask them to "
            "describe it in text if its contents matter to the answer.)"
        )
    api_key = _deepseek_api_key()
    selected_model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    if not api_key:
        return AIProviderResult("missing-secret", "deepseek", selected_model, "", {"error": "DEEPSEEK_API_KEY is not configured"})

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": selected_model, "messages": messages, "stream": False}
    request = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    timeout_seconds = _timeout_seconds()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except socket.timeout as exc:
        raise AIProviderTimeoutError(f"DeepSeek request timed out after {timeout_seconds} seconds") from exc
    except TimeoutError as exc:
        raise AIProviderTimeoutError(f"DeepSeek request timed out after {timeout_seconds} seconds") from exc
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AIProviderError(f"DeepSeek request failed with {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise AIProviderError(f"DeepSeek request failed: {exc}") from exc

    return AIProviderResult("completed", "deepseek", selected_model, _extract_text(raw), raw)


def _timeout_seconds() -> int:
    try:
        return max(10, min(int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", str(DEFAULT_DEEPSEEK_TIMEOUT_SECONDS))), 240))
    except ValueError:
        return DEFAULT_DEEPSEEK_TIMEOUT_SECONDS


def _extract_text(raw: dict[str, Any]) -> str:
    choices = raw.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "").strip()
