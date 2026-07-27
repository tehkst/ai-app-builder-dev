from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Optional

from app.platform.runtime.ai_provider import OPENAI_SECRET_NAME, AIProviderError, AIProviderTimeoutError

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 1536
DEFAULT_EMBEDDING_TIMEOUT_SECONDS = 30


def embeddings_configured() -> bool:
    return bool(os.getenv(OPENAI_SECRET_NAME))


def generate_embedding(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> Optional[list]:
    """Generate a real embedding vector via the OpenAI embeddings API.

    Returns None (rather than raising) when the provider isn't configured, so callers can
    treat "no embedding available" as a normal, degraded-but-honest state - matching the
    "unknown remains unknown" pattern used elsewhere in this platform - rather than a hard
    failure that blocks recording the episode itself.
    """
    api_key = os.getenv(OPENAI_SECRET_NAME)
    if not api_key:
        return None
    value = str(text or "").strip()
    if not value:
        return None

    payload = {"model": model, "input": value}
    request = urllib.request.Request(
        OPENAI_EMBEDDINGS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_EMBEDDING_TIMEOUT_SECONDS) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except socket.timeout as exc:
        raise AIProviderTimeoutError("OpenAI embeddings request timed out") from exc
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise AIProviderError("OpenAI embeddings request failed with %s: %s" % (exc.code, error_body)) from exc
    except urllib.error.URLError as exc:
        raise AIProviderError("OpenAI embeddings request failed: %s" % exc) from exc

    data = raw.get("data") or []
    if not data or not isinstance(data[0], dict):
        return None
    vector = data[0].get("embedding")
    if not isinstance(vector, list):
        return None
    return [float(item) for item in vector]


def pgvector_orm_enabled() -> bool:
    return os.getenv("PLATFORM_ENABLE_PGVECTOR_ORM", "false").lower() == "true"


def serialize_embedding(vector: list) -> Any:
    """Match the storage format the embedding_vector column actually expects.

    platform_semantic_embeddings.embedding_vector defaults to a plain Text column unless
    PLATFORM_ENABLE_PGVECTOR_ORM is set (see model_definitions/neural_data.py::_vector_type),
    so this must serialize consistently with whichever format is active.
    """
    if pgvector_orm_enabled():
        return vector
    return json.dumps(vector)


def deserialize_embedding(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        return [float(item) for item in parsed] if isinstance(parsed, list) else []
    try:
        return [float(item) for item in value]
    except TypeError:
        return []


def cosine_similarity(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
