import time
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

from app.core.llm import get_llm


llm = get_llm()


MAX_LLM_RETRIES = 3


def build_trace_config(
    *,
    node_name: str | None = None,
    project_id: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    trace_metadata = {
        "project_id": project_id,
        "node_name": node_name,
        **(metadata or {}),
    }

    return {
        "tags": [
            "ai-software-factory",
            *( [node_name] if node_name else [] ),
        ],
        "metadata": {
            key: value
            for key, value in trace_metadata.items()
            if value is not None
        },
    }


def invoke_llm(
    prompt: str,
    *,
    node_name: str | None = None,
    project_id: str | None = None,
    metadata: dict[str, Any] | None = None,
):

    last_error = None
    config = build_trace_config(
        node_name=node_name,
        project_id=project_id,
        metadata=metadata,
    )

    for attempt in range(MAX_LLM_RETRIES):

        try:
            return llm.invoke(prompt, config=config)

        except (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
        ) as error:

            last_error = error

            wait_time = 2 ** attempt

            print(
                f"LLM retry {attempt + 1}/{MAX_LLM_RETRIES}"
            )

            time.sleep(wait_time)

    raise last_error
