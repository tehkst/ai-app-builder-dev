from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


OPENAI_API_URL = "https://api.openai.com/v1/responses"
OPENAI_SECRET_NAME = "OPENAI_API_KEY"


@dataclass(frozen=True)
class AIProviderResult:
    status: str
    provider: str
    model: str
    output_text: str
    raw: dict[str, Any]


class AIProviderError(RuntimeError):
    pass


def provider_configured() -> bool:
    return bool(os.getenv(OPENAI_SECRET_NAME))


def invoke_openai(*, prompt: str, system: str | None = None, model: str | None = None) -> AIProviderResult:
    api_key = os.getenv(OPENAI_SECRET_NAME)
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-5.5")
    if not api_key:
        return AIProviderResult(
            status="missing-secret",
            provider="openai",
            model=selected_model,
            output_text="",
            raw={"error": "OPENAI_API_KEY is not configured"},
        )

    input_messages: list[dict[str, str]] = []
    if system:
        input_messages.append({"role": "system", "content": system})
    input_messages.append({"role": "user", "content": prompt})

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

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_text = response.read().decode("utf-8")
            raw = json.loads(raw_text)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise AIProviderError(f"OpenAI request failed with {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise AIProviderError(f"OpenAI request failed: {exc}") from exc

    return AIProviderResult(
        status="completed",
        provider="openai",
        model=selected_model,
        output_text=_extract_output_text(raw),
        raw=raw,
    )


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
