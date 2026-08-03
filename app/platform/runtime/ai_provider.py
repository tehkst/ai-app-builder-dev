from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


OPENAI_API_URL = "https://api.openai.com/v1/responses"
OPENAI_SECRET_NAME = "OPENAI_API_KEY"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 90


@dataclass(frozen=True)
class AIProviderResult:
    status: str
    provider: str
    model: str
    output_text: str
    raw: dict[str, Any]


class AIProviderError(RuntimeError):
    pass


class AIProviderTimeoutError(AIProviderError):
    pass


def _openai_api_key() -> str | None:
    from app.platform.credential_vault.service import resolve_credential

    return resolve_credential(OPENAI_SECRET_NAME)


def provider_configured() -> bool:
    return bool(_openai_api_key())


def invoke_openai(
    *, prompt: str, system: str | None = None, model: str | None = None, images: list[str] | None = None
) -> AIProviderResult:
    api_key = _openai_api_key()
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-5.5")
    if not api_key:
        return AIProviderResult(
            status="missing-secret",
            provider="openai",
            model=selected_model,
            output_text="",
            raw={"error": "OPENAI_API_KEY is not configured"},
        )

    input_messages: list[dict[str, Any]] = []
    if system:
        input_messages.append({"role": "system", "content": system})
    input_messages.append({"role": "user", "content": _user_content(prompt, images)})

    payload = {
        "model": selected_model,
        "input": input_messages,
    }
    request = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    timeout_seconds = _openai_timeout_seconds()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_text = response.read().decode("utf-8")
            raw = json.loads(raw_text)
    except socket.timeout as exc:
        raise AIProviderTimeoutError(
            f"OpenAI request timed out after {timeout_seconds} seconds"
        ) from exc
    except TimeoutError as exc:
        raise AIProviderTimeoutError(
            f"OpenAI request timed out after {timeout_seconds} seconds"
        ) from exc
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise AIProviderError(f"OpenAI request failed with {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, socket.timeout):
            raise AIProviderTimeoutError(
                f"OpenAI request timed out after {timeout_seconds} seconds"
            ) from exc
        raise AIProviderError(f"OpenAI request failed: {exc}") from exc

    return AIProviderResult(
        status="completed",
        provider="openai",
        model=selected_model,
        output_text=_extract_output_text(raw),
        raw=raw,
    )


def _user_content(prompt: str, images: list[str] | None) -> str | list[dict[str, str]]:
    """Build a Responses-API user content block, adding image parts only when real
    image data (a data: URI, read client-side from the attached file) is present -
    this is what actually lets a vision-capable model see an attached screenshot,
    rather than just being told a file was attached.
    """
    if not images:
        return prompt
    content: list[dict[str, str]] = [{"type": "input_text", "text": prompt}]
    for image_url in images:
        content.append({"type": "input_image", "image_url": image_url})
    return content


def _openai_timeout_seconds() -> int:
    raw_timeout = os.getenv("OPENAI_TIMEOUT_SECONDS", str(DEFAULT_OPENAI_TIMEOUT_SECONDS))
    try:
        timeout = int(raw_timeout)
    except ValueError:
        return DEFAULT_OPENAI_TIMEOUT_SECONDS
    return max(10, min(timeout, 240))


def _extract_output_text(raw: dict[str, Any]) -> str:
    direct = raw.get("output_text")
    if isinstance(direct, str):
        return direct

    pieces: list[str] = []
    output = raw.get("output") or []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        pieces.append(block["text"])
    return "\n".join(pieces).strip()
