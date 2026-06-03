import time
from typing import Any, Dict, Optional

from openai import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

from app.core.llm import get_llm
from app.ai.state import ProjectState


llm = get_llm()


MAX_LLM_RETRIES = 3
FACTORY_CODE_IMMUTABILITY_RULE = (
    "Generated-app requests must never mutate the core AI SaaS platform code. "
    "All generated customer app files must be written only inside the generated app workspace."
)


def build_trace_config(
    *,
    node_name: Optional[str] = None,
    project_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    trace_metadata = {
        "project_id": project_id,
        "node_name": node_name,
        **(metadata or {}),
    }

    return {
        "tags": [
            "ai-software-factory",
            *([node_name] if node_name else []),
        ],
        "metadata": {
            key: value
            for key, value in trace_metadata.items()
            if value is not None
        },
    }


def build_node_metadata(
    state: ProjectState,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "current_step": state.get("current_step"),
        "fix_attempts": state.get("fix_attempts", 0),
        "runtime_fix_attempts": state.get("runtime_fix_attempts", 0),
        "factory_code_immutability_rule": FACTORY_CODE_IMMUTABILITY_RULE,
        **(metadata or {}),
    }


def invoke_llm(
    prompt: str,
    *,
    node_name: Optional[str] = None,
    project_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
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


def invoke_node_llm(
    state: ProjectState,
    node_name: str,
    prompt: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
):
    return invoke_llm(
        prompt,
        node_name=node_name,
        project_id=state.get("project_id"),
        metadata=build_node_metadata(state, metadata),
    )
