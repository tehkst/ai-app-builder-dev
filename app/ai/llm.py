import time

from openai import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

from app.core.llm import get_llm


llm = get_llm()


MAX_LLM_RETRIES = 3


def invoke_llm(prompt: str):

    last_error = None

    for attempt in range(MAX_LLM_RETRIES):

        try:
            return llm.invoke(prompt)

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
